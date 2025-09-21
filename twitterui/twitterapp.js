const tweetInput = document.getElementById("tweetInput");
const tweetBtn = document.getElementById("tweetBtn");
const feed = document.getElementById("feed");
const searchInput = document.getElementById("search");

let tweets = JSON.parse(localStorage.getItem("tweets")) || [];

// Render feed
function renderTweets(filter = "") {
  feed.innerHTML = "";
  tweets
    .filter((t) => t.text.toLowerCase().includes(filter.toLowerCase()))
    .forEach((tweet, index) => {
      const tweetEl = document.createElement("div");
      tweetEl.className = "tweet";
      tweetEl.innerHTML = `
        <p>${tweet.text}</p>
        <small>${new Date(tweet.time).toLocaleString()}</small>
        <div class="actions">
          <span class="action-btn like-btn ${tweet.liked ? "liked" : ""}">❤️ ${tweet.likes}</span>
          <span class="action-btn delete-btn">🗑️ Delete</span>
        </div>
      `;

      

      feed.appendChild(tweetEl);
    });
}

// Save tweets locally
function saveTweets() {
  localStorage.setItem("tweets", JSON.stringify(tweets));
}

// Upload tweet to backend (then backend stores in S3)
async function postTweetToServer(tweet) {
  try {
    const response = await fetch("/post_tweet", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(tweet),
    });

    const data = await response.json();
    console.log("Tweet uploaded to S3:", data);
  } catch (error) {
    console.error("Error uploading tweet:", error);
  }
}

// Post new tweet
tweetBtn.addEventListener("click", () => {
  const text = tweetInput.value.trim();
  if (text) {
    const newTweet = {
      text,
      time: Date.now(),
      liked: false,
      likes: 0,
      user: "User123",        // optional user info
      location: "Kota Bharu", // optional location
    };

    // Save locally
    tweets.unshift(newTweet);
    saveTweets();
    renderTweets();

    // Send to backend for S3 storage
    postTweetToServer(newTweet);

    // Clear input
    tweetInput.value = "";
  }
});

// Search
searchInput.addEventListener("input", (e) => {
  renderTweets(e.target.value);
});

// Initial render
renderTweets();
