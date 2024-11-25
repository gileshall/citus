#!/usr/bin/env python

import requests
import openai
import json
import os
import hashlib
import textwrap
from datetime import datetime
from pprint import pformat

CACHE_DIR = "release_cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cache_filename(repo_name, tag_name):
    hash_object = hashlib.md5(f"{repo_name}-{tag_name}".encode())
    return os.path.join(CACHE_DIR, f"{hash_object.hexdigest()}.json")

def cache_release_data(repo_name, tag_name, data):
    cache_file = get_cache_filename(repo_name, tag_name)
    with open(cache_file, 'w') as f:
        json.dump(data, f)

def load_cached_release(repo_name, tag_name):
    cache_file = get_cache_filename(repo_name, tag_name)
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)
    return None

def get_releases(repo_name):
    url = f"https://api.github.com/repos/{repo_name}/releases"
    params = {'per_page': 100, 'page': 1}
    
    while True:
        response = requests.get(url, params=params)

        if response.status_code == 200:
            releases = response.json()
            if releases:
                for release in releases:
                    release_info = {
                        'name': release.get('name'),
                        'tag_name': release.get('tag_name'),
                        'published_at': release.get('published_at'),
                        'body': release.get('body'),
                        'prerelease': release.get('prerelease'),
                        'mentions_count': int(release.get('mentions_count', 0)),
                        'draft': release.get('draft')
                    }
                    yield release_info
            else:
                if params['page'] == 1:
                    print("No releases found for this repository.")
                break
            params['page'] += 1
        elif response.status_code == 404:
            print("Error: Repository not found. Please check the repository name.")
            break
        else:
            print(f"Error: Unable to fetch releases. Status code: {response.status_code}")
            break

def analyze_releases(repo_name, prompt, continue_on_error=True):
    cli = openai.OpenAI()
    
    for release in get_releases(repo_name):
        # Check if the release is already cached
        cached_release = load_cached_release(repo_name, release['tag_name'])
        if cached_release:
            dt = datetime.strptime(cached_release['published_at'], '%Y-%m-%dT%H:%M:%SZ')
            cached_release['published_at'] = dt.date().isoformat()
            yield cached_release
            continue

        release_text = (
            "Release Name: " + release['name'] + "\n" +
            "Tag Name: " + release['tag_name'] + "\n" +
            "Published Date: " + release['published_at'] + "\n" +
            "Body: " + (release['body'] if release['body'] else "None") + "\n" +
            "Pre-release: " + str(release['prerelease']) + "\n" +
            "Mentions Count: " + str(release.get('mentions_count', 'None')) + "\n" +
            "Draft: " + str(release.get('draft', 'None'))
        )
        
        messages = [
            {"role": "system", "content": [{"type": "text", "text": prompt}]},
            {"role": "user", "content": [{"type": "text", "text": release_text}]}
        ]

        analysis_result = {}
        try:
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
            analysis_result = json.loads(str(resp.choices[0].message.content).strip())
        except Exception as e:
            print(f"Error processing LLM response for release {release['name']}: {e}")
            if not continue_on_error:
                break

        # Update release dictionary with analysis
        release['analysis'] = analysis_result if analysis_result else {}
        cache_release_data(repo_name, release['tag_name'], release)

        yield release

# Example prompt to send to LLM
prompt = (
    "Scan the following GitHub release information (name, tag_name, published_at, body) and report the following as a well-formed JSON dictionary:\n"
    "- release_type (minor, major, security, beta, etc)\n"
    "- added_features (programs like HaplotypeCaller, cloud awareness, etc)\n"
    "- notes (text summary of anything significant mentioned in the release notes)"
)

def pretty_format_release(release):
    new_features = release['analysis'].get('added_features', [])
    new_features = '\n'.join([f'  - {ft}' for ft in new_features])
    ret = (
        f"Version: {release['name']}\n"
        f"Publish Date: {release['published_at']}\n"
        f"Release Type: {release['analysis'].get('release_type', 'None')}\n"
        f"New Features:\n{new_features}\n"
        f"\nNotes: {textwrap.fill(release['analysis'].get('notes', 'None'), width=120)}\n"
    )
    return ret

def get_version_data(repo_name, prompt, continue_on_error=False):
    itr = analyze_releases(repo_name, prompt, continue_on_error=continue_on_error)
    versions = []
    for (idx, release_info) in enumerate(itr):
        if idx > 0:
            print('-' * 120)
        versions.append(release_info)
        txt = pretty_format_release(release_info)
        print(txt.strip())
    return versions

repo_name = 'broadinstitute/gatk'
versions = get_version_data(repo_name, prompt)
with open('gatk_versions.json', 'w') as fh:
    json.dump(versions, fh, indent=2)
