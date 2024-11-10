import requests
from urllib.parse import urlencode, quote
import re
from datetime import datetime, timedelta

def generate_biorxiv_url(params=None, page=1):
    # Default parameters
    default_params = {
        'query': 'gatk',
        'jcode': 'medrxiv||biorxiv',
        'limit_from': '2024-01-01',
        'limit_to': '2024-11-30',
        'numresults': 100,
        'sort': 'relevance-rank',
        'format_result': 'condensed'
    }
    
    # If params is not provided, initialize as an empty dictionary
    if params is None:
        params = {}
    
    # Update default parameters with provided parameters
    final_params = {**default_params, **params}
    
    # Construct query string from the parameters
    query_parts = [
        quote(final_params['query']),
        f"jcode%3A{quote(final_params['jcode'])}",
        f"limit_from%3A{quote(final_params['limit_from'])}",
        f"limit_to%3A{quote(final_params['limit_to'])}",
        f"numresults%3A{final_params['numresults']}",
        f"sort%3A{quote(final_params['sort'])}",
        f"format_result%3A{quote(final_params['format_result'])}"
    ]
    query_string = '%20'.join(query_parts)
    
    # Construct final URL with pagination
    base_url = "https://www.biorxiv.org/search/"
    return f"{base_url}{query_string}?page={page}"

def extract_dois_from_html(html):
    # Regular expression to find DOI URIs in the HTML
    # https://stackoverflow.com/questions/27910/finding-a-doi-in-a-document-or-page
    doi_pattern = r'https://doi\.org/10\.\d{4,9}/[\w\.\-]+(?:/[\w\.\-]+)?'
    dois = re.findall(doi_pattern, html)
    return dois

def search_biorxiv_and_extract_dois(query, seen_dois=None, **kwargs):
    page = 1
    seen_dois = seen_dois if seen_dois is not None else set()

    while True:
        # Generate the URL using the search term, other parameters, and current page
        params = {'query': query, **kwargs}
        url = generate_biorxiv_url(params, page=page)
        
        # Download the HTML from the generated URL
        response = requests.get(url)
        if response.status_code == 200:
            html = response.text
            # Extract DOIs from the HTML
            dois = extract_dois_from_html(html)
            dois = set(dois) - seen_dois
            # If no DOIs are found, break the loop
            if not dois:
                break

            yield from dois
            seen_dois = seen_dois.union(dois)
            page += 1
        else:
            raise Exception(f"Failed to fetch URL: {url} with status code {response.status_code}")

def date_range_iterator(start_date='1970-01-01', end_date=None, interval=None):
    # Convert string dates to datetime objects
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d') if end_date else datetime.today()
    
    # Default interval is the entire range if none is provided
    if interval is None:
        interval = (end - start).days
    
    delta = timedelta(days=interval)
    current_start = start

    while current_start < end:
        current_end = min(current_start + delta, end)
        yield (current_start.strftime('%Y-%m-%d'), current_end.strftime('%Y-%m-%d'))
        current_start = current_end

if __name__ == '__main__':
    # Example usage of date_range_iterator for the first three months of January 2023, week by week
    for start, end in date_range_iterator(start_date='2023-01-01', end_date='2023-03-31', interval=7):
        print(f"Start Date: {start}, End Date: {end}")
        dois = list(search_biorxiv_and_extract_dois('gatk', limit_from=start, limit_to=end))
        print(f"DOIs found: {dois}")
