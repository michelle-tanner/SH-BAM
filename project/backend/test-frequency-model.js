const db = require("./db");
const { tagFeedback } = require("./agents/tagger");

console.log("🛠️  Testing Top-5 Tag Frequency Model...");

// 1. Insert some test feedback
const testData = [
  { rating: 5, comment: "Super fast and very helpful!" },
  { rating: 4, comment: "It was good, decent performance." },
  { rating: 2, comment: "Really slow and unhelpful." },
  { rating: 5, comment: "Amazing performance, I love it." },
  { rating: 1, comment: "Terrible lag and crashed twice." },
  { rating: 5, comment: "Helpful and awesome!" }
];

testData.forEach(item => {
  const feedback = db.insertFeedback(item.rating, item.comment);
  const tags = tagFeedback(item.comment, item.rating);
  if (tags.length > 0) {
    db.insertTags(feedback.id, tags);
  }
});

// 2. Fetch the top 5 tags with feedback
console.log("\n📊 Top Tags Analysis:");
const topTags = db.getTopTagsWithFeedback(5);

if (topTags.length === 0) {
  console.log("No tags found. Something might be wrong.");
} else {
  topTags.forEach(t => {
    console.log(`\n🔸 [${t.tag}] - Frequency: ${t.frequency}`);
    t.feedbacks.forEach((f, idx) => {
      console.log(`   ${idx + 1}. Rating: ${f.rating}/5 | Comment: "${f.comment || ''}"`);
    });
  });
}

console.log("\n✅ Test completed.");
