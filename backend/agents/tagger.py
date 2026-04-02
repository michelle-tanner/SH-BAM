# agents/tagger.py
# -----------------
# Agent 1 — Tagger
#
# Responsibility:
#   Receives a feedback comment (rating ≤ 3) after it has been saved to the
#   database, and assigns one or more category tags to it.
#
# Behaviour:
#   Pass 1 — attempts to match the comment against the current active tag list
#             stored in the `tags` table, with a confidence score per tag.
#   Pass 2 — if no existing tag scores above the confidence threshold, asks
#             the model to propose a new tag (name + description), which is
#             then inserted into `tags` with created_by = 'agent'.
#
# Writes to:
#   feedback_tags  – one row per tag assigned to the feedback submission
#   tags           – only when a net-new tag is created
#
# Triggered by:
#   POST /feedback in main.py via FastAPI BackgroundTasks (non-blocking).
#
# Model:
#   Ollama (OLLAMA_MODEL in .env). Swappable to Claude by changing the client.
