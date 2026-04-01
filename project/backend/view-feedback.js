const db = require("./db");

console.log("\n📊 Top 5 Tags Current Summary:");
const topTags = db.getTopTagsWithFeedback(5);

if (topTags.length === 0) {
  console.log("   No feedback data found in the database yet.");
} else {
  topTags.forEach(t => {
    console.log(`🔸 [${t.tag}] - Frequency: ${t.frequency}`);
    t.feedbacks.forEach((f, idx) => {
      console.log(`   ${idx + 1}. Rating: ${f.rating}/5 | Comment: "${f.comment || ''}"`);
    });
    console.log(); // Add a blank line between tags
  });
}
