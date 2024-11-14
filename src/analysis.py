import os
import json
from openai import OpenAI
from datetime import datetime

prompts_path = os.path.join(os.path.dirname(__file__), 'prompts')
analyze_article_path = os.path.join(prompts_path, "analyze_article.txt")

with open(analyze_article_path) as fh:
    system_prompt = fh.read()

def analyze_article(article_path):
    with open(article_path) as fh:
        article_text = fh.read()

    cli = OpenAI()
    messages = [
        {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
        {"role": "user", "content": [{"type": "text", "text": article_text}]},
    ]

    resp = cli.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.25,
        max_tokens=2048,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        response_format={"type": "json_object"}
    )
    return json.loads(str(resp.choices[0].message.content).strip())
