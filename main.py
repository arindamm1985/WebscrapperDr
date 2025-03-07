import os
import re
import requests
from flask import Flask, render_template, request
from bs4 import BeautifulSoup
from googlesearch import search  # Install with: pip install google
import openai

app = Flask(__name__)

# Set your OpenAI API key in your Render.com environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

def fetch_meta_data(url):
    """Fetches the title, meta description, and meta keywords from a website."""
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Extract title
    title_tag = soup.find("title")
    title = title_tag.text.strip() if title_tag else ""
    
    # Extract meta description
    description = ""
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        description = meta_desc["content"].strip()
    
    # Extract meta keywords (if available)
    meta_keywords = ""
    meta_kw = soup.find("meta", attrs={"name": "keywords"})
    if meta_kw and meta_kw.get("content"):
        meta_keywords = meta_kw["content"].strip()
    
    return title, description, meta_keywords

def extract_keywords_openai(text, top_n=5):
    """
    Uses OpenAI's Completion API to extract the top N relevant keywords from the provided text.
    Returns a list of keywords.
    """
    prompt = (
        f"Extract the top {top_n} relevant keywords from the following text. "
        "Return the keywords as a comma-separated list.\n\n"
        f"{text}\n\nKeywords:"
    )
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            temperature=0.3,
            max_tokens=60,
            n=1
        )
        keywords_str = response.choices[0].text.strip()
        keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
        return keywords
    except Exception as e:
        print("Error using OpenAI API:", e)
        return []

def get_google_ranking(keyword, domain, num_results=20):
    """
    Searches Google for the given keyword and returns the ranking position
    of the website (if found within the top num_results).
    """
    try:
        results = list(search(keyword, num_results=num_results, stop=num_results, pause=2))
        for idx, result in enumerate(results):
            if domain in result:
                return idx + 1  # Rankings are 1-indexed
        return "Not Found"
    except Exception as e:
        return f"Error: {e}"

@app.route("/", methods=["GET", "POST"])
def index():
    results = None
    website_url = ""
    meta_info = None
    if request.method == "POST":
        website_url = request.form.get("website_url")
        if website_url:
            try:
                title, description, meta_keywords = fetch_meta_data(website_url)
                meta_info = {"title": title, "description": description, "meta_keywords": meta_keywords}
                combined_text = f"{title} {description} {meta_keywords}"
                top_keywords = extract_keywords_openai(combined_text, top_n=5)
                # Extract the domain (e.g., example.com) from the URL
                domain = re.sub(r'^https?://(www\.)?', '', website_url).split('/')[0]
                results = []
                for keyword in top_keywords:
                    ranking = get_google_ranking(keyword, domain)
                    results.append({"Keyword": keyword, "Google Ranking": ranking})
            except Exception as e:
                results = [{"Keyword": "Error", "Google Ranking": str(e)}]
    return render_template("index.html", website_url=website_url, meta_info=meta_info, results=results)

if __name__ == "__main__":
    app.run(debug=True)
