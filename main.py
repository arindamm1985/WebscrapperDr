import requests
import nltk
nltk.download('punkt_tab')
nltk.download('averaged_perceptron_tagger')
nltk.download('averaged_perceptron_tagger_eng')
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk import pos_tag, RegexpParser
from fastapi import FastAPI, Header, HTTPException
import os
import uvicorn
from bs4 import BeautifulSoup
from googlesearch import search  # Install with: pip install google
import re
from pydantic import BaseModel 
from openai import OpenAI
from collections import Counter
import string
from flask import Flask, request, jsonify
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = FastAPI() 
class FetchRequest(BaseModel):
    website_url: str
def fetch_meta_data(url):
    """
    Fetches the title, meta keywords, and meta description from a website.
    """
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        raise Exception(f"Error fetching URL: {e}")
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Extract title
    title_tag = soup.find("title")
    title = title_tag.text.strip() if title_tag else ""
    
    # Extract meta keywords
    meta_keywords = ""
    meta_kw = soup.find("meta", attrs={"name": "keywords"})
    if meta_kw and meta_kw.get("content"):
        meta_keywords = meta_kw["content"].strip()
    
    # Extract meta description
    meta_description = ""
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        meta_description = meta_desc["content"].strip()
    
    return title, meta_keywords, meta_description

def extract_keywords(title, meta_keywords,meta_description):
    """
    Extract candidate keywords by splitting the title and meta keywords.
    
    1. Splits the title by the pipe ('|') and comma (',') characters.
    2. Splits the meta keywords by commas.
    3. Combines and returns a unique list of keywords.
    """
    keywords = []
    
    # Process title: split by '|' then by ','
    if title:
        for part in title.split("|"):
            for subpart in part.split(","):
                keyword = subpart.strip()
                if keyword and keyword not in keywords:
                    keywords.append(keyword)

    combined_text = ""
    if title:
        combined_text += title + " "
    if meta_description:
        combined_text += meta_description
    
    # Extract key noun phrases (main objects) using a simple grammar
    sentences = sent_tokenize(combined_text)
    grammar = "NP: {<DT>?<JJ>*<NN.*>+}"
    cp = RegexpParser(grammar)
    extracted_objects = set()
    
    for sentence in sentences:
        tokens = word_tokenize(sentence)
        tagged = pos_tag(tokens)
        tree = cp.parse(tagged)
        for subtree in tree.subtrees():
            if subtree.label() == 'NP':
                # Reconstruct the phrase from the leaves
                phrase = " ".join(word for word, tag in subtree.leaves())
                # Filter out single-word phrases to avoid noise
                if len(phrase.split()) > 1:
                    extracted_objects.add(phrase)
    
    # Append the extracted main objects to the keywords list if they are unique
    for phrase in extracted_objects:
        if phrase not in keywords:
            keywords.append(phrase)
                    
    # Process meta keywords: split by ','
    if meta_keywords:
        for keyword in meta_keywords.split(","):
            keyword = keyword.strip()
            if keyword and keyword not in keywords:
                keywords.append(keyword)
    
    return keywords
    
def get_google_ranking(keyword, domain, num_results=20):
    """
    Searches Google for the given keyword and returns the ranking position
    of the website (if found within the top num_results).
    """
    try:
        results = list(search(keyword, num_results=num_results,region="in"))
        for idx, result in enumerate(results):
            if domain in result:
                return idx + 1  # Rankings are 1-indexed
        return "Not Found"
    except Exception as e:
        return f"Error: {e}"

def get_google_ranking_list(keyword, num_results=20):
    """
    Searches Google for the given keyword and returns the ranking position
    of the website (if found within the top num_results).
    """
    try:
        results = list(search(keyword, num_results=num_results,region="in"))
        return {"search_result":results}
    except Exception as e:
        return f"Error: {e}"

@app.post("/api/fetch")
def extract(req: FetchRequest):


    website_url = req.website_url
    
    try:
        # Fetch meta data
        title, meta_keywords, meta_description = fetch_meta_data(website_url)
        top_keywords = extract_keywords(title, meta_keywords,meta_description)
        
        # Extract the domain (e.g., example.com) from the URL
        domain = re.sub(r'^https?://(www\.)?', '', website_url).split('/')[0]
        
        # For each keyword, get the Google ranking
        results = []
        for keyword in top_keywords:
            ranking = get_google_ranking(keyword, domain)
            resulitems = get_google_ranking_list(keyword)
            results.append({"keyword": keyword, "google_ranking": ranking,"search_result":resulitems})
        
        response_payload = {
            "website": website_url,
            "meta": {
                "title": title,
                "meta_keywords": meta_keywords,
                "meta_description": meta_description,
            },
            "top_keywords": top_keywords,
            "rankings": results
        }
        return response_payload
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
   uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
