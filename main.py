import requests
import os
from bs4 import BeautifulSoup
from googlesearch import search  # Install with: pip install google
import re
from openai import OpenAI
from collections import Counter
import string
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
def fetch_meta_data(url):
    """Fetch the title, meta description, and meta keywords from a website."""
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

# Define a basic list of stopwords
stopwords = {
    "the", "and", "is", "in", "to", "of", "a", "with", "for", "on", "that",
    "by", "this", "it", "as", "at", "from", "an", "be", "are", "or", "we",
    "you", "our", "us", "not", "have", "has"
}

def extract_keywords_openai(text, top_n=5):
    """
    Uses OpenAI's standard Completion API to extract the top N relevant keywords
    from the provided text. Returns a list of keywords.
    """
    prompt = (
        f"Extract the top {top_n} relevant keywords from the following text. "
        "Return the keywords as a comma-separated list.\n\n"
        f"{text}\n\nKeywords:"
    )
    
    try:
        response =openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
        )
        keywords_str = response.choices[0].message.content.strip()
        # Split the comma-separated response into a list of keywords
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
        results = list(search(keyword, num_results=num_results))
        for idx, result in enumerate(results):
            if domain in result:
                return idx + 1  # Rankings are 1-indexed
        return "Not Found"
    except Exception as e:
        return f"Error: {e}"

def main(website_url):
    # Display website header
    print(f"Website: {website_url}\n")
    
    # Fetch meta data from the website
    title, description, meta_keywords = fetch_meta_data(website_url)
    print(f"Title: {title}")
    print(f"Description: {description}")
    print(f"Meta Keywords: {meta_keywords}\n")
    
    # Combine meta data to extract keywords
    combined_text = f"{title} {description} {meta_keywords}"
    top_keywords = extract_keywords_openai(combined_text, top_n=5)
    print("Top 5 Relevant Keywords:", top_keywords, "\n")
    
    # Extract the domain (e.g., example.com) from the URL
    domain = re.sub(r'^https?://(www\.)?', '', website_url).split('/')[0]
    
    # Prepare results for each keyword
    results = []
    for keyword in top_keywords:
        ranking = get_google_ranking(keyword, domain)
        results.append({"Keyword": keyword, "Google Ranking": ranking})
    
    # Print final results in table format
    print(f"Results for Website: {website_url}")
    print("{:<20} {:<15}".format("Keyword", "Google Ranking"))
    print("-" * 35)
    for row in results:
        print("{:<20} {:<15}".format(row["Keyword"], str(row["Google Ranking"])))

if __name__ == "__main__":
    # Replace with the target website URL
    website = "https://www.mullerfirm.com/"
    
