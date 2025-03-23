from flask import Flask, request, jsonify, send_from_directory, render_template
import requests
from textblob import TextBlob
from gtts import gTTS
import os
import nltk
from wordcloud import WordCloud
import matplotlib
matplotlib.use('Agg')  # Set the backend to 'Agg'
import matplotlib.pyplot as plt
import io
import base64
from nltk import pos_tag
from datetime import datetime, timedelta

# Set a custom NLTK data path
# custom_path = '/Users/tslee/nltk_data'
# os.makedirs(custom_path, exist_ok=True)
# nltk.data.path.append(custom_path)

# # Download NLTK data
# nltk.download('punkt')
# nltk.download('averaged_perceptron_tagger')
# nltk.download('wordnet')
import nltk
import os

# Set NLTK data path to a writable directory
nltk_data_path = "/tmp/nltk_data"
os.makedirs(nltk_data_path, exist_ok=True)
nltk.data.path.append(nltk_data_path)

# Download NLTK data
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('wordnet')


app = Flask(__name__)

# Function to read API keys from file
def read_api_keys(file_path="apikeys.txt"):
    """
    Reads API keys from a file.
    """
    api_keys = {}
    try:
        with open(file_path, "r") as file:
            for line in file:
                if "=" in line:
                    key, value = line.strip().split("=")
                    api_keys[key] = value
        return api_keys
    except FileNotFoundError:
        raise FileNotFoundError(f"{file_path} not found. Please create the file and add your API keys.")

# Read API keys
api_keys = read_api_keys()
NEWS_API_KEY = api_keys.get("NEWS_API_KEY")
GUARDIAN_API_KEY = api_keys.get("GUARDIAN_API_KEY")

# Fetch news from News API
def fetch_news_newsapi(keyword, from_date):
    url = f"https://newsapi.org/v2/everything?q={keyword}&apiKey={NEWS_API_KEY}&pageSize=5&from={from_date}"
    response = requests.get(url)
    return response.json()

# Fetch news from The Guardian API
def fetch_news_guardian(keyword, from_date):
    url = f"https://content.guardianapis.com/search?q={keyword}&api-key={GUARDIAN_API_KEY}&page-size=5&from-date={from_date}"
    response = requests.get(url)
    return response.json()

# Extract positive and negative keywords with sentiment scores
def extract_keywords(news_text):
    blob = TextBlob(news_text)
    keywords = {
        "positive": {},
        "negative": {}
    }
    for sentence in blob.sentences:
        # Tokenize the sentence into words
        words = sentence.words
        # Use NLTK's pos_tag instead of TextBlob's tags
        tagged_words = pos_tag(words)
        for word, pos in tagged_words:
            if pos.startswith('NN'):  # Only consider nouns
                sentiment = sentence.sentiment.polarity
                if sentiment > 0:
                    keywords["positive"][word] = sentiment
                elif sentiment < 0:
                    keywords["negative"][word] = abs(sentiment)
    return keywords

# Generate a word cloud for positive and negative keywords
def generate_wordcloud(keywords):
    # Combine positive and negative keywords
    word_freq = {**keywords["positive"], **{k: -v for k, v in keywords["negative"].items()}}

    # Check if there are any keywords to plot
    if not word_freq:
        return None  # No keywords to plot

    # Generate word cloud
    wordcloud = WordCloud(
        width=400,
        height=200,
        background_color='white',
        colormap='RdYlGn',  # Red-Yellow-Green colormap
        relative_scaling=0.5
    ).generate_from_frequencies(word_freq)

    # Convert word cloud to base64 image
    plt.figure(figsize=(8, 4))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    wordcloud_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()  # Close the plot to free up memory

    return wordcloud_base64

# Convert news to speech (only for English articles)
def text_to_speech(text, filename="news.mp3"):
    tts = gTTS(text=text, lang="en")
    tts.save(filename)
    return filename

# API endpoint to fetch news and keywords
@app.route("/news", methods=["GET"])
def get_news():
    keyword = request.args.get("keyword", "stock market")
    months_back = int(request.args.get("months_back", 1))  # Default: 1 month
    from_date = (datetime.now() - timedelta(days=30 * months_back)).strftime("%Y-%m-%d")

    results = []
    all_keywords = {"positive": {}, "negative": {}}

    # Fetch news from NewsAPI
    newsapi_data = fetch_news_newsapi(keyword, from_date)
    articles = newsapi_data.get("articles", [])
    for i, article in enumerate(articles[:5]):  # Limit to top 5 articles
        # Handle cases where title or description is None
        title = article.get("title", "") or ""
        description = article.get("description", "") or ""
        url = article.get("url", "#")
        published_at = article.get("publishedAt", "")
        language = article.get("language", "en")  # Default to English

        # Format the date
        if published_at:
            published_at = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ").strftime("%B %d, %Y")

        news_text = f"{title} {description}".strip()  # Combine title and description
        keywords = extract_keywords(news_text)

        # Merge keywords from all articles
        for sentiment, words in keywords.items():
            for word, score in words.items():
                if word in all_keywords[sentiment]:
                    all_keywords[sentiment][word] += score
                else:
                    all_keywords[sentiment][word] = score

        # Convert news title to speech (only for English articles)
        audio_file = None
        if language == "en":
            audio_file = text_to_speech(title, f"news_{i}.mp3")

        results.append({
            "title": title,
            "description": description,
            "url": url,
            "published_at": published_at,
            "keywords": keywords,
            "audio_url": f"/audio/{audio_file}" if audio_file else None,
            "language": language
        })

    # Fetch news from The Guardian API
    guardian_data = fetch_news_guardian(keyword, from_date)
    articles = guardian_data.get("response", {}).get("results", [])
    for i, article in enumerate(articles[:5]):  # Limit to top 5 articles
        title = article.get("webTitle", "") or ""
        url = article.get("webUrl", "#")
        published_at = article.get("webPublicationDate", "")
        language = "en"  # Guardian API articles are in English

        # Format the date
        if published_at:
            published_at = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ").strftime("%B %d, %Y")

        news_text = title  # Guardian API does not provide a description
        keywords = extract_keywords(news_text)

        # Merge keywords from all articles
        for sentiment, words in keywords.items():
            for word, score in words.items():
                if word in all_keywords[sentiment]:
                    all_keywords[sentiment][word] += score
                else:
                    all_keywords[sentiment][word] = score

        # Convert news title to speech (only for English articles)
        audio_file = text_to_speech(title, f"guardian_{i}.mp3")

        results.append({
            "title": title,
            "description": "",  # Guardian API does not provide a description
            "url": url,
            "published_at": published_at,
            "keywords": keywords,
            "audio_url": f"/audio/{audio_file}",
            "language": language
        })

    # Generate word cloud for all keywords (if valid keywords exist)
    wordcloud_base64 = None
    if all_keywords["positive"] or all_keywords["negative"]:
        wordcloud_base64 = generate_wordcloud(all_keywords)

    return jsonify({
        "articles": results,
        "wordcloud": wordcloud_base64,
        "message": "No keywords found for word cloud." if not wordcloud_base64 else None
    })

# Serve audio files
@app.route("/audio/<filename>")
def serve_audio(filename):
    return send_from_directory(".", filename)

# Root route
@app.route("/")
def home():
    return render_template("roboRadio.html")

# if __name__ == "__main__":
#     app.run(debug=True)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)