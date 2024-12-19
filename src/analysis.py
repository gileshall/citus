import os
import json
from openai import OpenAI

# Module-level variable for prompts path
PROMPTS_PATH = os.path.join(os.path.dirname(__file__), 'prompts')

def find_prompt_file(prompt_name):
    """
    Resolve the prompt file based on the given prompt name.
    If the prompt name is an absolute path, use it directly.
    Otherwise, search in the prompts directory for a matching file.
    """
    if os.path.isabs(prompt_name):
        return prompt_name
    
    matching_prompts = [
        fname for fname in os.listdir(PROMPTS_PATH)
        if prompt_name.lower() in fname.lower()
    ]

    if len(matching_prompts) == 0:
        raise FileNotFoundError(f"No prompt found matching '{prompt_name}'.")
    elif len(matching_prompts) > 1:
        raise ValueError(f"Multiple prompts found matching '{prompt_name}': {matching_prompts}")

    return os.path.join(PROMPTS_PATH, matching_prompts[0])

def analyze_article(article_path, prompt_name):
    # Resolve prompt file
    prompt_path = find_prompt_file(prompt_name)

    # Read the selected prompt file
    with open(prompt_path) as fh:
        system_prompt = fh.read()

    # Read the article content
    with open(article_path) as fh:
        article_text = fh.read()

    # Create OpenAI client and prepare messages
    cli = OpenAI()
    messages = [
        {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
        {"role": "user", "content": [{"type": "text", "text": article_text}]},
    ]

    # Call OpenAI API
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

    # Parse and return the response
    return json.loads(str(resp.choices[0].message.content).strip())
