const db = require("../db");

const DEFAULT_THRESHOLD = parseInt(process.env.ALERT_THRESHOLD, 10) || 5;

/**
 * Check the stored tag_frequencies model and create alerts
 * for any tag that has crossed the threshold.
 *
 * @param {number} [threshold] – minimum count to trigger an alert
 * @returns {{ triggered: Array, all: Array }}
 */
function analyzeAndAlert(threshold = DEFAULT_THRESHOLD) {
  const frequencies = db.getTagFrequencies();
  const triggered = [];

  for (const { tag, count } of frequencies) {
    if (count >= threshold) {
      // Don't duplicate pending alerts for the same tag
      const existing = db.getPendingAlerts().find((a) => a.tag === tag);
      if (!existing) {
        // Grab sample feedback IDs that have this tag
        const sampleIds = db.db
          .prepare(
            "SELECT DISTINCT feedback_id FROM feedback_tags WHERE tag = ? ORDER BY feedback_id DESC LIMIT 5"
          )
          .all(tag)
          .map((r) => r.feedback_id);

        db.createAlert(tag, count, sampleIds);
        triggered.push({ tag, count, sampleIds });
        console.log(
          `🚨 ALERT: Tag "${tag}" reached ${count} occurrences (threshold: ${threshold})`
        );
      }
    }
  }

  return { triggered, all: frequencies };
}

/**
 * Build a human-readable summary of pending alerts with sample feedback.
 */
function getAlertSummary() {
  const alerts = db.getPendingAlerts();
  return alerts.map((alert) => {
    const sampleIds = JSON.parse(alert.sample_ids || "[]");
    const samples = db.getFeedbackByIds(sampleIds);
    return {
      id: alert.id,
      tag: alert.tag,
      count: alert.count,
      status: alert.status,
      created_at: alert.created_at,
      samples: samples.map((s) => ({
        id: s.id,
        rating: s.rating,
        comment: s.comment,
        tags: s.tags,
        created_at: s.created_at,
      })),
    };
  });
}

module.exports = { analyzeAndAlert, getAlertSummary };
