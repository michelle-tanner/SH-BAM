const db = require("./db");

console.log("\n📜 All Stored Feedback:");
const allFeedback = db.getAllFeedback();

if (allFeedback.length === 0) {
  console.log("   No feedback data found in the database yet.");
} else {
  allFeedback.forEach((f, index) => {
    console.log(`\n--- Feedback #${f.id} ---`);
    console.log(`⭐ Rating: ${f.rating} / 5`);
    console.log(`💬 Comment: "${f.comment || '(No comment provided)'}"`);
    console.log(`🏷️  Tags: [${f.tags || 'none'}]`);
    console.log(`📅 Date: ${new Date(f.created_at).toLocaleString()}`);
  });
  console.log(`\nTotal Feedback Count: ${allFeedback.length}\n`);
}
