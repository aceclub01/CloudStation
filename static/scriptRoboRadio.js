let audioFiles = [];  // Array to store audio file URLs
let currentIndex = 0;  // Index of the currently playing audio file
let readArticles = new Set();  // Track read articles
let playedAudioFiles = new Set();  // Track played audio files

// Function to play the next audio file
function playNext() {
    if (currentIndex < audioFiles.length) {
        const audioFile = audioFiles[currentIndex];
        document.getElementById("audio").src = audioFile;
        document.getElementById("audio").play();
        playedAudioFiles.add(audioFile);  // Mark audio file as played
        currentIndex++;
    } else {
        // Stop playback if all audio files have been played
        document.getElementById("audio").pause();
    }
}

// Event listener for when the audio ends
document.getElementById("audio").addEventListener("ended", playNext);

// Fetch news and update audio files
document.getElementById("newsForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const keyword = document.getElementById("keyword").value;
    const monthsBack = document.getElementById("months_back").value;
    const response = await fetch(`/news?keyword=${keyword}&months_back=${monthsBack}`);
    const data = await response.json();

    // Clear previous news and audio files
    document.getElementById("news").innerHTML = "";
    document.getElementById("keywords").innerHTML = "";
    audioFiles = [];
    playedAudioFiles.clear();  // Reset played audio files
    currentIndex = 0;  // Reset the audio playback index

    // Display word cloud or message
    if (data.wordcloud) {
        document.getElementById("wordcloud").innerHTML = `<img src="data:image/png;base64,${data.wordcloud}" alt="Word Cloud">`;
    } else {
        document.getElementById("wordcloud").innerHTML = `<p>${data.message}</p>`;
    }

    // Display news and keywords
    data.articles.forEach((article, index) => {
        if (!readArticles.has(article.url)) {  // Skip read articles
            document.getElementById("news").innerHTML += `
                <div class="article">
                    <p><strong>Title ${index + 1}:</strong> <a href="${article.url}" target="_blank">${article.title}</a></p>
                    <p><strong>Date:</strong> ${article.published_at}</p>
                    <p><strong>Description:</strong> ${article.description}</p>
                    <p><strong>Positive Keywords:</strong> ${Object.keys(article.keywords.positive).join(", ")}</p>
                    <p><strong>Negative Keywords:</strong> ${Object.keys(article.keywords.negative).join(", ")}</p>
                    <hr>
                </div>
            `;
            if (article.audio_url && !playedAudioFiles.has(article.audio_url)) {
                audioFiles.push(article.audio_url);  // Add audio file to the playlist
            }
            readArticles.add(article.url);  // Mark article as read
        }
    });

    // Start playing the first audio file
    if (audioFiles.length > 0) {
        playNext();
    }
});