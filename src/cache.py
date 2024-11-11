import os
import re
import json
import requests
from urllib.parse import urlparse
from functools import wraps
from crossref import restful as xref
from grobid import extract_text
from tei import convert_tei_to_text

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
    def url(self):
        """
        Construct the full DOI URL from prefix and suffix.
        """
        return f"https://doi.org/{self._prefix}/{self._suffix}"

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

    def format_filename(self, stem):
        suffix = self.doi_reference.suffix.split('/')
        suffix = '_'.join(suffix)
        if stem[0] != '.':
            return f"{self.doi_reference.prefix}_{suffix}_{stem}"
        return f"{self.doi_reference.prefix}_{suffix}{stem}"

    def get_link_to_paper(self):
        def sort_key(link):
            pdf_priority = 1 if link['content-type'] == 'application/pdf' else 0
            vor_priority = 1 if link['content-version'] == 'vor' else 0
            syndication_priority = 1 if link['intended-application'] == 'syndication' else 0
            return (pdf_priority, vor_priority, syndication_priority)

        link_list = self.xref.get('link')
        link_list = sorted(link_list, key=sort_key, reverse=True)
        if not link_list:
            msg = f"Could not find a paper link for {self.doi_reference}"
            raise ValueError(msg)

        paper_link = link_list[0]
        return paper_link['URL']

    def download_pdf(self):
        paper_url = self.get_link_to_paper()
        pdf_filename = self.format_filename('.pdf')
        pdf_path = os.path.join(self.cache_path, pdf_filename)
        if os.path.exists(pdf_path):
            return pdf_path

        # Headers to make the request look like it's coming from a desktop browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/pdf",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://academic.oup.com/"
        }

        # XXX: try different versions if this doesn't work?
        resp = requests.get(paper_url, headers=headers, allow_redirects=True)
        if resp.status_code != 200:
            msg = f"Failed to download PDF at {url}. Status code: {response.status_code}"
            raise ValueError(msg)

        with open(pdf_path, "wb") as fh:
            fh.write(resp.content)

        return pdf_path

    def extract_text(self):
        pdf_path = self.download_pdf()
        tei_filename = self.format_filename('.tei.xml')
        tei_path = os.path.join(self.cache_path, tei_filename)
        extract_text(pdf_path, tei_path)
        txt_filename = self.format_filename('.txt')
        txt_path = os.path.join(self.cache_path, txt_filename)
        convert_tei_to_text(tei_path, txt_path)
        return txt_path

    def load_xref_data(self):
        filename = self.format_filename('xref.json')
        filepath = os.path.join(self.cache_path, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as fh:
                info = json.load(fh)
        else:
            work = xref.Works()
            info = work.doi(self.doi_reference.url)
            with open(filepath, 'w') as fh:
                json.dump(info, fh, indent=2)
        return info

    @property
    def xref(self):
        if not hasattr(self, '_xref'):
            self._xref = self.load_xref_data()
        return self._xref
    
    def is_preprint_of(self):
        #{'is-preprint-of': [{'asserted-by': 'subject',
         # 'id': '10.1093/bioinformatics/btac729',
         #'id-type': 'doi'}]}
        if 'relation' in self.xref:
            if 'is-preprint-of' in self.xref['relation']:
                ppo = self.xref['relation']['is-preprint-of']
                if len(ppo) > 1:
                    msg = f'is_preprint_of() multiple successors for {self.doi_reference.url}: {ppo}'
                    raise ValueError(msg)
                if ppo[0]['id-type'] != 'doi':
                    msg = f'is_preprint_of(): non doi ID {self.doi_reference.url}: {ppo}'
                    raise ValueError(msg)
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
    #doi = "https://doi.org/10.1101/2023.12.12.571258"
    #doi = "https://doi.org/10.1101/460345"
    #doi = "https://doi.org/10.1093/bioinformatics/btac729"
    doi = "https://doi.org/10.1101/2022.04.21.488948"
    doi_obj = resolve_doi(doi)
    doi_obj.download_pdf()
    text_path = doi_obj.extract_text()
