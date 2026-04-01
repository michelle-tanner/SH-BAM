const Database = require("better-sqlite3");
const path = require("path");

const DB_PATH = path.join(__dirname, "feedback.db");
const db = new Database(DB_PATH);

// Enable WAL mode for better performance
db.pragma("journal_mode = WAL");

// ── Schema ──────────────────────────────────────────────────────────────────
db.exec(`
  CREATE TABLE IF NOT EXISTS feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    rating      INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    comment     TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS feedback_tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_id INTEGER NOT NULL REFERENCES feedback(id),
    tag         TEXT NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS tag_frequencies (
    tag         TEXT PRIMARY KEY,
    count       INTEGER NOT NULL DEFAULT 0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tag         TEXT NOT NULL,
    count       INTEGER NOT NULL,
    sample_ids  TEXT,
    status      TEXT DEFAULT 'pending',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
  );
`);

// ── Feedback helpers ────────────────────────────────────────────────────────

/** Insert new feedback and return the row */
function insertFeedback(rating, comment) {
  const stmt = db.prepare(
    "INSERT INTO feedback (rating, comment) VALUES (?, ?)"
  );
  const info = stmt.run(rating, comment || null);
  return { id: info.lastInsertRowid, rating, comment };
}

/** Get all feedback entries with their tags */
function getAllFeedback() {
  return db.prepare(`
    SELECT f.*, GROUP_CONCAT(ft.tag) as tags
    FROM feedback f
    LEFT JOIN feedback_tags ft ON ft.feedback_id = f.id
    GROUP BY f.id
    ORDER BY f.created_at DESC
  `).all();
}

/** Get feedback by id with tags */
function getFeedbackById(id) {
  const feedback = db.prepare("SELECT * FROM feedback WHERE id = ?").get(id);
  if (!feedback) return null;
  const tags = db
    .prepare("SELECT tag FROM feedback_tags WHERE feedback_id = ?")
    .all(id)
    .map((r) => r.tag);
  return { ...feedback, tags };
}

/** Get sample feedback entries for given IDs */
function getFeedbackByIds(ids) {
  if (!ids.length) return [];
  const placeholders = ids.map(() => "?").join(",");
  return db
    .prepare(
      `SELECT f.*, GROUP_CONCAT(ft.tag) as tags
     FROM feedback f
     LEFT JOIN feedback_tags ft ON ft.feedback_id = f.id
     WHERE f.id IN (${placeholders})
     GROUP BY f.id`
    )
    .all(...ids);
}

// ── Tags helpers ────────────────────────────────────────────────────────────

/** Attach tags to a feedback entry AND update the frequency model */
function insertTags(feedbackId, tags) {
  const insertTag = db.prepare(
    "INSERT INTO feedback_tags (feedback_id, tag) VALUES (?, ?)"
  );
  const upsertFreq = db.prepare(`
    INSERT INTO tag_frequencies (tag, count, last_updated)
    VALUES (?, 1, CURRENT_TIMESTAMP)
    ON CONFLICT(tag) DO UPDATE SET
      count = count + 1,
      last_updated = CURRENT_TIMESTAMP
  `);

  const run = db.transaction((tags) => {
    for (const tag of tags) {
      insertTag.run(feedbackId, tag);
      upsertFreq.run(tag);
    }
  });
  run(tags);
}

/** Get all tag frequencies from the stored model */
function getTagFrequencies() {
  return db
    .prepare("SELECT * FROM tag_frequencies ORDER BY count DESC")
    .all();
}

/** Get top N tags with their associated feedback (ratings and comments) */
function getTopTagsWithFeedback(limit = 5) {
  return db
    .prepare(`
      SELECT 
        t.tag, 
        COUNT(t.feedback_id) as frequency,
        json_group_array(
          json_object('rating', f.rating, 'comment', f.comment)
        ) as feedbacks
      FROM feedback_tags t
      JOIN feedback f ON t.feedback_id = f.id
      GROUP BY t.tag
      ORDER BY frequency DESC
      LIMIT ?
    `)
    .all(limit)
    .map(row => ({
      tag: row.tag,
      frequency: row.frequency,
      feedbacks: JSON.parse(row.feedbacks)
    }));
}

// ── Alerts helpers ──────────────────────────────────────────────────────────

/** Create an alert for human review */
function createAlert(tag, count, sampleIds) {
  const stmt = db.prepare(
    "INSERT INTO alerts (tag, count, sample_ids) VALUES (?, ?, ?)"
  );
  return stmt.run(tag, count, JSON.stringify(sampleIds));
}

/** Get pending alerts */
function getPendingAlerts() {
  return db
    .prepare(
      "SELECT * FROM alerts WHERE status = 'pending' ORDER BY created_at DESC"
    )
    .all();
}

/** Update alert status */
function updateAlertStatus(id, status) {
  return db
    .prepare("UPDATE alerts SET status = ? WHERE id = ?")
    .run(status, id);
}

module.exports = {
  db,
  insertFeedback,
  getAllFeedback,
  getFeedbackById,
  getFeedbackByIds,
  insertTags,
  getTagFrequencies,
  getTopTagsWithFeedback,
  createAlert,
  getPendingAlerts,
  updateAlertStatus,
};
