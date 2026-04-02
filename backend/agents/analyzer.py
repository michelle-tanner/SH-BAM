# agents/analyzer.py
# -------------------
# Agent 2 — Analyzer
#
# Responsibility:
#   Runs after the Tagger completes. Counts how frequently each tag has
#   appeared across all feedback submissions and triggers a human alert
#   when a tag crosses the threshold defined in FEEDBACK_ALERT_THRESHOLD (.env).
#
# Behaviour:
#   1. Queries `feedback_tags` to count occurrences of each active tag.
#   2. For any tag at or above the threshold that has not already been queued,
#      writes a summary row to `review_queue` (tag name, frequency, up to 3
#      sample comments).
#   3. Sends an alert email to ALERT_EMAIL_TO via Gmail SMTP using the
#      credentials in .env (ALERT_EMAIL_FROM + EMAIL_APP_PASSWORD).
#   4. Periodically checks the `tags` table for semantic overlap between tags
#      and proposes merges (marks redundant tags inactive, re-points their
#      feedback_tags rows to the surviving tag).
#
# Writes to:
#   review_queue  – one row per tag that crosses the alert threshold
#   tags          – updates is_active and merged_into when merging duplicate tags
#   feedback_tags – re-points rows when a tag is merged
#
# Triggered by:
#   tagger.py on completion (chained call), so it runs in the same
#   FastAPI background task.
#
# Model:
#   Ollama (OLLAMA_MODEL in .env) for semantic merge detection.
#   Swappable to Claude by changing the client.
#
# Email:
#   smtplib (Python stdlib) + Gmail SMTP. No extra package required.
#   Credentials loaded from .env via python-dotenv.
