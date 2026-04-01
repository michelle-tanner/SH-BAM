/**
 * Local keyword-based tagger — no external API needed.
 * Scans the feedback comment for keyword patterns and assigns 1-3 category tags.
 */

const TAG_RULES = [
  {
    tag: "inaccurate",
    keywords: ["wrong", "incorrect", "inaccurate", "false", "error", "mistake", "not true", "misleading", "factually"],
  },
  {
    tag: "incomplete",
    keywords: ["incomplete", "missing", "left out", "didn't cover", "not enough detail", "partial", "more info", "need more"],
  },
  {
    tag: "irrelevant",
    keywords: ["irrelevant", "off topic", "didn't answer", "not related", "wrong topic", "not what i asked", "unrelated"],
  },
  {
    tag: "confusing",
    keywords: ["confusing", "unclear", "hard to understand", "didn't make sense", "complicated", "vague", "ambiguous"],
  },
  {
    tag: "too_long",
    keywords: ["too long", "verbose", "wordy", "too much", "shorter", "concise", "rambling", "lengthy"],
  },
  {
    tag: "too_short",
    keywords: ["too short", "brief", "not detailed", "need more", "expand", "elaborate", "shallow", "surface level"],
  },
  {
    tag: "outdated",
    keywords: ["outdated", "old", "deprecated", "out of date", "obsolete", "no longer", "was removed"],
  },
  {
    tag: "tone",
    keywords: ["tone", "rude", "condescending", "too formal", "too casual", "unprofessional", "attitude"],
  },
  {
    tag: "formatting",
    keywords: ["formatting", "format", "layout", "hard to read", "messy", "structure", "organized", "bullet"],
  },
  {
    tag: "slow",
    keywords: ["slow", "took too long", "wait", "loading", "lag", "speed", "timeout", "delayed"],
  },
];

/**
 * Tag a feedback comment using local keyword matching.
 * @param {string} comment - the user's free-text feedback
 * @param {number} rating  - the numeric rating (1-5)
 * @returns {string[]} array of matched tag strings
 */
function tagFeedback(comment, rating) {
  if (!comment || !comment.trim()) return ["other"];

  const lower = comment.toLowerCase();
  const matched = [];

  for (const rule of TAG_RULES) {
    for (const kw of rule.keywords) {
      if (lower.includes(kw)) {
        matched.push(rule.tag);
        break; // one match per tag is enough
      }
    }
  }

  // Cap at 3 tags
  if (matched.length > 3) {
    return matched.slice(0, 3);
  }

  // If nothing matched, assign "other"
  return matched.length > 0 ? matched : ["other"];
}

module.exports = { tagFeedback };
