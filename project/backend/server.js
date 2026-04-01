require("dotenv").config();

const express = require("express");
const cors = require("cors");
const db = require("./db");
const { tagFeedback } = require("./agents/tagger");
const { analyzeAndAlert, getAlertSummary } = require("./agents/analyzer");

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

// ── Health check ────────────────────────────────────────────────────────────
app.get("/api/health", (_req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

// ── Submit feedback ─────────────────────────────────────────────────────────
app.post("/api/feedback", (req, res) => {
  try {
    const { rating, comment } = req.body;

    if (!rating || typeof rating !== "number" || rating < 1 || rating > 5) {
      return res.status(400).json({ error: "Rating must be between 1 and 5" });
    }

    // 1. Store the feedback (rating + comment)
    const feedback = db.insertFeedback(rating, comment);
    console.log(`📝 Feedback #${feedback.id} — rating: ${rating}`);
    if (comment) {
      console.log(`   💬 Comment: "${comment}"`);
    }

    // 2. Run local tagger if there's a comment
    let tags = [];
    if (comment && comment.trim()) {
      tags = tagFeedback(comment, rating);
      db.insertTags(feedback.id, tags);
      console.log(`   🏷️  Tags: [${tags.join(", ")}]`);

      // 3. Run analyzer to check frequency thresholds
      const analysis = analyzeAndAlert();
      if (analysis.triggered.length > 0) {
        console.log(`   🚨 ${analysis.triggered.length} new alert(s) triggered`);
      }
    }

    // 4. Show top tags summary automatically when feedback is submitted
    console.log(`\n📊 Top 5 Tags Summary:`);
    const topTags = db.getTopTagsWithFeedback(5);
    topTags.forEach(t => {
      console.log(`   🔸 [${t.tag}] (Freq: ${t.frequency})`);
      t.feedbacks.slice(0, 3).forEach(f => {
        console.log(`      ↳ Rating: ${f.rating}/5 | "${f.comment || ''}"`);
      });
      if (t.feedbacks.length > 3) console.log(`      ↳ ... and ${t.feedbacks.length - 3} more`);
    });
    console.log();

    res.json({ success: true, feedback: { ...feedback, tags } });
  } catch (err) {
    console.error("Error processing feedback:", err);
    res.status(500).json({ error: "Failed to process feedback" });
  }
});

// ── Get all feedback ────────────────────────────────────────────────────────
app.get("/api/feedback", (_req, res) => {
  try {
    res.json(db.getAllFeedback());
  } catch (err) {
    console.error("Error fetching feedback:", err);
    res.status(500).json({ error: "Failed to fetch feedback" });
  }
});

// ── Get tag frequency model ─────────────────────────────────────────────────
app.get("/api/tags", (_req, res) => {
  try {
    res.json(db.getTagFrequencies());
  } catch (err) {
    console.error("Error fetching tags:", err);
    res.status(500).json({ error: "Failed to fetch tag frequencies" });
  }
});

// ── Get top tags with associated feedback ──────────────────────────────────
app.get("/api/tags/top", (req, res) => {
  try {
    const limit = parseInt(req.query.limit, 10) || 5;
    res.json(db.getTopTagsWithFeedback(limit));
  } catch (err) {
    console.error("Error fetching top tags:", err);
    res.status(500).json({ error: "Failed to fetch top tags with feedback" });
  }
});

// ── Get pending alerts ──────────────────────────────────────────────────────
app.get("/api/alerts", (_req, res) => {
  try {
    res.json(getAlertSummary());
  } catch (err) {
    console.error("Error fetching alerts:", err);
    res.status(500).json({ error: "Failed to fetch alerts" });
  }
});

// ── Update alert status ─────────────────────────────────────────────────────
app.patch("/api/alerts/:id", (req, res) => {
  try {
    const { status } = req.body;
    if (!["reviewed", "dismissed"].includes(status)) {
      return res.status(400).json({ error: "Status must be 'reviewed' or 'dismissed'" });
    }
    db.updateAlertStatus(req.params.id, status);
    res.json({ success: true });
  } catch (err) {
    console.error("Error updating alert:", err);
    res.status(500).json({ error: "Failed to update alert" });
  }
});

// ── Manually trigger analysis ───────────────────────────────────────────────
app.post("/api/analyze", (_req, res) => {
  try {
    res.json(analyzeAndAlert());
  } catch (err) {
    console.error("Error running analysis:", err);
    res.status(500).json({ error: "Failed to run analysis" });
  }
});

// ── Start ───────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`\n🚀 Feedback server running on http://localhost:${PORT}`);
  console.log(`   Alert threshold: ${process.env.ALERT_THRESHOLD || 5}`);
  console.log(`   Tagger: local keyword matching (no API key needed)`);
  console.log(`   Database: feedback.db\n`);
});
