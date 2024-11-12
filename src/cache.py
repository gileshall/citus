import os
import re
import json
import sys
import logging
import requests
import doi2pdf
from urllib.parse import urlparse
from functools import wraps
from crossref import restful as xref
from grobid import extract_text
from tei import convert_tei_to_text, DEFAULT_SECTIONS_ORDER
from analysis import analyze_article

# when we convert the article to text for LLM analysis
# we leave out 'authors' and 'references'
# because they take up a lot of tokens, but do not add a lot of information

ARTICLE_SECTION_ORDERING = list(DEFAULT_SECTIONS_ORDER)
del ARTICLE_SECTION_ORDERING[ARTICLE_SECTION_ORDERING.index('authors')]
del ARTICLE_SECTION_ORDERING[ARTICLE_SECTION_ORDERING.index('references')]

class DOIReference:
    def __init__(self, doi_input):
        if isinstance(doi_input, DOIReference):
            # Clone the DOIReference object
            self._prefix = doi_input._prefix
            self._suffix = doi_input._suffix
        else:
            self.doi_input = doi_input
            self._prefix, self._suffix = self._parse_doi(doi_input)

    def _parse_doi(self, doi_input):
        if '/' in doi_input:
            if doi_input.startswith('https://doi.org/'):
                doi_input = doi_input[len('https://doi.org/'):]
            parts = doi_input.split('/')
            return (parts[0], '/'.join(parts[1:]))
        else:
            raise ValueError("Invalid DOI input, must contain '/' to separate prefix and suffix")

    @property
    def stem(self):
        return f"{self._prefix}/{self._suffix}"

    @property
    def url(self):
        return f"https://doi.org/{self.stem}"
    
    def __str__(self):
        return self.url

    @property
    def prefix(self):
        return self._prefix

    @property
    def suffix(self):
        return self._suffix
    
class DOI:
    def __init__(self, cache_path, doi_reference):
        if not isinstance(doi_reference, DOIReference):
            doi_reference = DOIReference(doi_reference)
        self.doi_reference = doi_reference
        self.cache_path = cache_path

        # Create directory if it does not exist
        if not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)

        # Set up logging specific to this module
        log_filename = os.path.join(self.cache_path, 'process.log')
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler(log_filename)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)
        self.logger.propagate = False
        
        self.logger.info(f"Initialized DOI object for {self.doi_reference}")

    def format_filename(self, stem):
        suffix = self.doi_reference.suffix.split('/')
        suffix = '_'.join(suffix)
        if stem[0] != '.':
            return f"{self.doi_reference.prefix}_{suffix}_{stem}"
        return f"{self.doi_reference.prefix}_{suffix}{stem}"

    def get_links_to_paper(self):
        def sort_key(link):
            pdf_priority = 1 if link['content-type'] == 'application/pdf' else 0
            vor_priority = 1 if link['content-version'] == 'vor' else 0
            syndication_priority = 1 if link['intended-application'] == 'syndication' else 0
            return (pdf_priority, vor_priority, syndication_priority)

        link_list = self.xref.get('link')
        link_list = sorted(link_list, key=sort_key, reverse=True)
        if not link_list:
            msg = f"Could not find a paper link for {self.doi_reference}"
            self.logger.error(msg)
            raise ValueError(msg)

        self.logger.info(f"Found {len(link_list)} links to paper for {self.doi_reference}")
        return link_list

    def download_pdf(self):
        pdf_filename = self.format_filename('.pdf')
        pdf_path = os.path.join(self.cache_path, pdf_filename)
        if os.path.exists(pdf_path):
            self.logger.info(f"PDF already exists at {pdf_path}")
            return pdf_path

        if self.download_pdf_method_one(pdf_path):
            self.logger.info(f"Downloaded PDF using method one for {self.doi_reference}")
            return pdf_path

        if self.download_pdf_method_two(pdf_path):
            self.logger.info(f"Downloaded PDF using method two for {self.doi_reference}")
            return pdf_path

        msg = f"Failed to download PDF for {self.doi_reference}."
        self.logger.error(msg)
        raise ValueError(msg)

    def download_pdf_method_two(self, pdf_path):
        try:
            doi2pdf.doi2pdf(self.doi_reference.stem, output=pdf_path)
            self.logger.info(f"Successfully downloaded PDF using doi2pdf for {self.doi_reference}")
            return pdf_path
        except doi2pdf.main.NotFoundError:
            self.logger.warning(f"doi2pdf method failed for {self.doi_reference}")
            return None

    def download_pdf_method_one(self, pdf_path):
        # Headers to make the request look like it's coming from a desktop browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/pdf",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://academic.oup.com/"
        }
        links = self.get_links_to_paper()
        for link in links:
            paper_url = link['URL']
            resp = requests.get(paper_url, headers=headers, allow_redirects=True)
            if resp.status_code != 200:
                self.logger.warning(f"Failed to download from {paper_url} with status code {resp.status_code}")
                continue

            with open(pdf_path, "wb") as fh:
                fh.write(resp.content)
            self.logger.info(f"Successfully downloaded PDF from {paper_url}")
            return pdf_path

    def extract_text(self):
        pdf_path = self.download_pdf()
        tei_filename = self.format_filename('.tei.xml')
        tei_path = os.path.join(self.cache_path, tei_filename)
        self.logger.info(f"Extracting text to TEI format at {tei_path}")
        extract_text(pdf_path, tei_path)
        txt_filename = self.format_filename('.txt')
        txt_path = os.path.join(self.cache_path, txt_filename)
        self.logger.info(f"Converting TEI to plain text at {txt_path}")
        convert_tei_to_text(tei_path, txt_path)
        return txt_path
    
    def analyze_article(self):
        try:
            txt_path = self.extract_text()
            analysis_filename = self.format_filename('analysis.json')
            analysis_path = os.path.join(self.cache_path, analysis_filename)
            if not os.path.exists(analysis_path):
                self.logger.info(f"Analyzing article text at {txt_path}")
                analysis = analyze_article(txt_path)
                with open(analysis_path, 'w') as fh:
                    json.dump(analysis, fh, indent=2)
                self.logger.info(f"Analysis saved to {analysis_path}")
            else:
                self.logger.info(f"Analysis already exists at {analysis_path}")
            return analysis_path
        except Exception as e:
            self.logger.error(f"Exception occurred during analyze_article: {str(e)}", exc_info=True)
            raise

    def load_xref_data(self):
        filename = self.format_filename('xref.json')
        filepath = os.path.join(self.cache_path, filename)
        if os.path.exists(filepath):
            self.logger.info(f"Loading cached Crossref data from {filepath}")
            with open(filepath, 'r') as fh:
                info = json.load(fh)
        else:
            self.logger.info(f"Fetching Crossref data for {self.doi_reference.url}")
            work = xref.Works()
            info = work.doi(self.doi_reference.url)
            with open(filepath, 'w') as fh:
                json.dump(info, fh, indent=2)
            self.logger.info(f"Crossref data saved to {filepath}")
        return info

    @property
    def xref(self):
        if not hasattr(self, '_xref'):
            self._xref = self.load_xref_data()
        return self._xref
    
    def is_preprint_of(self):
        if 'relation' in self.xref:
            if 'is-preprint-of' in self.xref['relation']:
                ppo = self.xref['relation']['is-preprint-of']
                if len(ppo) > 1:
                    msg = f'is_preprint_of() multiple successors for {self.doi_reference.url}: {ppo}'
                    self.logger.error(msg)
                    raise ValueError(msg)
                if ppo[0]['id-type'] != 'doi':
                    msg = f'is_preprint_of(): non doi ID {self.doi_reference.url}: {ppo}'
                    self.logger.error(msg)
                    raise ValueError(msg)
                self.logger.info(f"DOI {self.doi_reference.url} is a preprint of {ppo[0]['id']}")
                return ppo[0]['id']

class DOIFactory:
    def __init__(self, base_path='./doi-cache'):
        self.base_path = base_path
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)

    def create_doi(self, doi_input):
        doi_reference = DOIReference(doi_input)
        cache_dir = self._get_cache_directory(doi_reference)
        return DOI(cache_path=cache_dir, doi_reference=doi_reference)

    def _get_cache_directory(self, doi_reference):
        suffix = doi_reference.suffix.split('/')
        suffix = '_'.join(suffix)
        return os.path.join(self.base_path, doi_reference.prefix, suffix)

def resolve_doi(doi, preprint_cutoff=10):
    factory = DOIFactory()
    for level in range(preprint_cutoff):
        doi_obj = factory.create_doi(doi)
        ppo_doi = doi_obj.is_preprint_of()
        if ppo_doi:
            doi = ppo_doi
            continue
        return doi_obj

# Example usage
if __name__ == "__main__":
    from pprint import pprint
    doi = sys.argv[1]
    doi_obj = resolve_doi(doi)
    text_path = doi_obj.analyze_article()
    pprint(json.loads(open(text_path).read()))
