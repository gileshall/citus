import os
import re
import json
import sys
import logging
import requests
import doi2pdf
from datetime import datetime
from urllib.parse import urlparse
from functools import wraps
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from crossref import restful as xref
from grobid import extract_text
from tei import convert_tei_to_text, DEFAULT_SECTIONS_ORDER
from persist import PersistentDict
from analysis import analyze_article
from __init__ import __version__
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# when we convert the article to text for LLM analysis
# we leave out 'authors' and 'references'
# because they take up a lot of tokens, but do not add a lot of information

BODY_SECTION_ORDERING = list(DEFAULT_SECTIONS_ORDER)
del BODY_SECTION_ORDERING[BODY_SECTION_ORDERING.index('authors')]
del BODY_SECTION_ORDERING[BODY_SECTION_ORDERING.index('references')]

def validate_pdf(filepath):
    try:
        PdfReader(filepath)
    except PdfReadError:
        return False
    return True

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
            raise ValueError(f"Invalid DOI input '{doi_input}', must contain '/' to separate prefix and suffix")

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
    def __init__(self, cache_path, doi, preprint_doi=None):
        if preprint_doi is not None:
            preprint_doi = DOIReference(preprint_doi)
        self.doi = DOIReference(doi)
        self.preprint_doi = preprint_doi
        self.cache_path = cache_path

        # Create directory if it does not exist
        if not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)

        # Mark its creation
        if 'created_at' not in self.status:
            self.status['created_at'] = datetime.utcnow().isoformat()
            self.status['__version__'] = __version__

        # Set up logging specific to this module
        log_filename = os.path.join(self.cache_path, 'process.log')
        self.logger = logging.getLogger(self.doi.stem)
        if not self.logger.hasHandlers():
            self.logger.setLevel(logging.DEBUG)
            
            # File handler without colors
            file_handler = logging.FileHandler(log_filename)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(file_handler)
            
            # Stream handler with colors
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(self.ColoredFormatter())
            self.logger.addHandler(stream_handler)
            
            self.logger.propagate = False
        
        self.logger.info(f"Initialized DOI object for {self.doi}")

    class ColoredFormatter(logging.Formatter):
        def format(self, record):
            log_fmt = (
                f"{Fore.GREEN}%(asctime)s{Style.RESET_ALL} - "
                f"{Fore.CYAN}%(name)s{Style.RESET_ALL} - "
                f"{Fore.YELLOW}%(levelname)s{Style.RESET_ALL} - "
                f"{Fore.WHITE}%(message)s{Style.RESET_ALL}"
            )
            formatter = logging.Formatter(log_fmt)
            return formatter.format(record)

    def format_filename(self, stem):
        suffix = self.doi.suffix.split('/')
        suffix = '_'.join(suffix)
        if stem[0] != '.':
            return f"{self.doi.prefix}_{suffix}_{stem}"
        return f"{self.doi.prefix}_{suffix}{stem}"

    def get_links_to_paper(self):
        if not self.is_published:
            link_list = []
            version = 1
            if self.preprint_info:
                version = self.preprint_info[-1]["version"]
            for server in ('biorxiv', 'medrxiv'):
                url = {"URL": f"https://www.{server}.org/content/10.1101/2020.10.13.337071v{version}.full.pdf"}
                link_list.append(url)
            return link_list

        def sort_key(link):
            pdf_priority = 1 if link['content-type'] == 'application/pdf' else 0
            vor_priority = 1 if link['content-version'] == 'vor' else 0
            syndication_priority = 1 if link['intended-application'] == 'syndication' else 0
            return (pdf_priority, vor_priority, syndication_priority)

        link_list = self.xref.get('link')
        link_list = sorted(link_list, key=sort_key, reverse=True)
        if not link_list:
            msg = f"Could not find a paper link for {self.doi}"
            self.logger.error(msg)
            raise ValueError(msg)

        self.logger.info(f"Found {len(link_list)} links to paper for {self.doi}")
        return link_list

    def download_pdf(self):
        pdf_filename = self.format_filename('.pdf')
        pdf_path = os.path.join(self.cache_path, pdf_filename)
        if os.path.exists(pdf_path):
            self.logger.info(f"PDF already exists at {pdf_path}")
            return pdf_path

        if self.download_pdf_method_one(pdf_path):
            self.logger.info(f"Downloaded PDF using method one for {self.doi.stem} to {pdf_path}")
            self.status['pdf_downloaded'] = True
            return pdf_path

        if self.download_pdf_method_two(pdf_path):
            self.logger.info(f"Downloaded PDF using method two for {self.doi.stem} to {pdf_path}")
            self.status['pdf_downloaded'] = True
            return pdf_path

        if self.download_pdf_method_three(pdf_path):
            self.logger.info(f"Downloaded PDF using method three for {self.doi.stem} to {pdf_path}")
            self.status['pdf_downloaded'] = True
            return pdf_path

        msg = f"Failed to download PDF for {self.doi.stem}."
        self.logger.error(msg)
        raise ValueError(msg)

    def download_pdf_method_three(self, pdf_path):
        if self.preprint_doi:
            self.logger.info(f"Attempting to download pre-print {self.preprint_doi.stem} for {self.doi.stem}")
            factory = DOIFactory()
            pp_obj = factory.create_doi(doi=self.preprint_doi.stem)
            try:
                pp_pdf_path = pp_obj.download_pdf()
                rel_pp_pdf_path = os.path.relpath(pp_pdf_path, self.cache_path)
                os.symlink(rel_pp_pdf_path, pdf_path)
                return pdf_path
            except ValueError:
                pass

    def download_pdf_method_two(self, pdf_path):
        try:
            doi2pdf.doi2pdf(self.doi.stem, output=pdf_path)
            if not validate_pdf(pdf_path):
                os.unlink(pdf_path)
                self.logger.warning(f"Failed to download actual PDF with doi2pdf")
                return None
            self.logger.info(f"Successfully downloaded PDF using doi2pdf for {self.doi}")
            return pdf_path
        except doi2pdf.main.NotFoundError:
            self.logger.warning(f"doi2pdf method failed for {self.doi}")
            return None

    def download_pdf_method_one(self, pdf_path):
        # Headers to make the request look like it's coming from a desktop browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/pdf",
            "Accept-Language": "en-US,en;q=0.9",
            #"Referer": "https://academic.oup.com/"
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
            if not validate_pdf(pdf_path):
                os.unlink(pdf_path)
                self.logger.warning(f"Failed to download actual PDF from {paper_url}")
                continue
            self.logger.info(f"Successfully downloaded PDF from {paper_url}")
            return pdf_path

    def convert_pdf(self):
        tei_filename = self.format_filename('.tei.xml')
        tei_path = os.path.join(self.cache_path, tei_filename)
        if not os.path.exists(tei_path):
            pdf_path = self.download_pdf()
            extract_text(pdf_path, tei_path)
            self.logger.info(f"Extracted text from {pdf_path} to TEI format at {tei_path}")
            self.status['pdf_converted'] = True
        return tei_path

    def extract_body_from_tei(self):
        txt_filename = self.format_filename('body.txt')
        txt_path = os.path.join(self.cache_path, txt_filename)
        if not os.path.exists(txt_path):
            tei_path = self.convert_pdf()
            convert_tei_to_text(tei_path, txt_path, section_order=BODY_SECTION_ORDERING)
            self.logger.info(f"Extracted body from {tei_path} to {txt_path}")
            self.status['text_body_extracted'] = True
        return txt_path
    
    def extract_authors_from_tei(self):
        txt_filename = self.format_filename('authors.txt')
        txt_path = os.path.join(self.cache_path, txt_filename)
        if not os.path.exists(txt_path):
            tei_path = self.convert_pdf()
            convert_tei_to_text(tei_path, txt_path, section_order=('authors',))
            self.logger.info(f"Extracted authors from {tei_path} to {txt_path}")
            self.status['text_authors_extracted'] = True
        return txt_path

    def extract_references_from_tei(self):
        txt_filename = self.format_filename('references.txt')
        txt_path = os.path.join(self.cache_path, txt_filename)
        if not os.path.exists(txt_path):
            tei_path = self.convert_pdf()
            convert_tei_to_text(tei_path, txt_path)
            self.logger.info(f"Extracted references from {tei_path} to {txt_path}")
            self.status['text_references_extracted'] = True
        return txt_path

    def extract_text(self):
        self.extract_references_from_tei()
        self.extract_authors_from_tei()
        return self.extract_body_from_tei()

    def analyze_article(self, prompt_name=None):
        if not self.is_published:
            self.logger.info(f"{self.doi.stem} is not published, skipping analysis")
            return None
        try:
            txt_path = self.extract_text()
            analysis_filename = self.format_filename('analysis.json')
            analysis_path = os.path.join(self.cache_path, analysis_filename)
            if not os.path.exists(analysis_path):
                self.logger.info(f"Analyzing article text at {txt_path}")
                analysis = analyze_article(txt_path, prompt_name)
                with open(analysis_path, 'w') as fh:
                    json.dump(analysis, fh, indent=2)
                self.logger.info(f"Analysis saved to {analysis_path}")
            else:
                self.logger.info(f"Analysis already exists at {analysis_path}")
            self.status['article_analyzed'] = True
            return analysis_path
        except Exception as e:
            self.logger.error(f"Exception occurred during analyze_article: {str(e)}", exc_info=True)
            raise

    def load_preprint_info(self):
        filename = self.format_filename('preprint_info.json')
        filepath = os.path.join(self.cache_path, filename)

        if os.path.exists(filepath):
            self.logger.info(f"Loading cached rxiv data from {filepath}")
            with open(filepath, 'r') as fh:
                info = json.load(fh)
        else:
            # we don't know which server the preprint will be on
            info = []
            servers = ('biorxiv', 'medrxiv')
            for server in servers:
                url = f"https://api.biorxiv.org/details/{server}/{self.doi.stem}"
                resp = requests.get(url)
                if resp.status_code == 200:
                    # fetch it
                    info = resp.json().get('collection', list())
                    self.logger.info(f"Fetched preprint info for {self.doi.url} from {url}")
                    break

            with open(filepath, 'w') as fh:
                json.dump(info, fh, indent=2)
                self.logger.info(f"preprint info saved to {filepath}")

        return info

    def load_xref_data(self):
        filename = self.format_filename('xref.json')
        filepath = os.path.join(self.cache_path, filename)
        if os.path.exists(filepath):
            self.logger.info(f"Loading cached Crossref data from {filepath}")
            with open(filepath, 'r') as fh:
                info = json.load(fh)
        else:
            self.logger.info(f"Fetching Crossref data for {self.doi.url}")
            work = xref.Works()
            info = work.doi(self.doi.url)
            with open(filepath, 'w') as fh:
                json.dump(info, fh, indent=2)
            self.logger.info(f"Crossref data saved to {filepath}")
        return info

    @property
    def preprint_info(self):
        if not hasattr(self, '_preprint_info'):
            self._preprint_info = self.load_preprint_info()
        return self._preprint_info

    @property
    def xref(self):
        if not hasattr(self, '_xref'):
            self._xref = self.load_xref_data()
        return self._xref
    
    def is_preprint_of(self):
        # attempt one
        if len(self.preprint_info):
            publish_doi = self.preprint_info[-1].get('published')
            if publish_doi:
                self.status['is_preprint_of'] = publish_doi
                return publish_doi
        # attempt two
        if 'relation' in self.xref:
            if 'is-preprint-of' in self.xref['relation']:
                ppo = self.xref['relation']['is-preprint-of']
                if len(ppo) > 1:
                    msg = f'is_preprint_of() multiple successors for {self.doi.url}: {ppo}'
                    self.logger.error(msg)
                    raise ValueError(msg)
                if ppo[0]['id-type'] != 'doi':
                    msg = f'is_preprint_of(): non doi ID {self.doi.url}: {ppo}'
                    self.logger.error(msg)
                    raise ValueError(msg)
                self.logger.info(f"DOI {self.doi.url} is a preprint of {ppo[0]['id']}")
                self.status['is_preprint_of'] = ppo[0]['id']
                return ppo[0]['id']

    @property
    def is_published(self):
        if not hasattr(self, '_is_published'):
            self._is_published = ("published-print" in self.xref) or ("published-online" in self.xref)
            self.status['is_published'] = self._is_published
        return self._is_published
    
    @property
    def status(self):
        if not hasattr(self, '_status'):
            status_filename = self.format_filename("status.json")
            status_filepath = os.path.join(self.cache_path, status_filename)
            self._status = PersistentDict(status_filepath)
        return self._status

class DOIFactory:
    DefaultBaseCachePath = "./doi-cache"

    def __init__(self, base_cache_path=None):
        self.base_cache_path = base_cache_path or self.DefaultBaseCachePath
        if not os.path.exists(self.base_cache_path):
            os.makedirs(self.base_cache_path)

    def create_doi(self, doi, **kw):
        doi = DOIReference(doi)
        cache_dir = self._get_cache_directory(doi)
        return DOI(cache_path=cache_dir, doi=doi, **kw)

    def _get_cache_directory(self, doi):
        suffix = doi.suffix.split('/')
        suffix = '_'.join(suffix)
        return os.path.join(self.base_cache_path, doi.prefix, suffix)

def resolve_doi(doi, preprint_cutoff=10, cache_path=None):
    factory = DOIFactory(base_cache_path=cache_path)
    preprint_doi = None
    for level in range(preprint_cutoff):
        doi_obj = factory.create_doi(doi, preprint_doi=preprint_doi)
        ppo_doi = doi_obj.is_preprint_of()
        if ppo_doi:
            preprint_doi = doi
            doi = ppo_doi
            continue
        return doi_obj

# Example usage
if __name__ == "__main__":
    from pprint import pprint
    doi = sys.argv[1]
    prompt_name = sys.argv[2]
    doi_obj = resolve_doi(doi)
    text_path = doi_obj.analyze_article(prompt_name=prompt_name)
    pprint(json.loads(open(text_path).read()))
