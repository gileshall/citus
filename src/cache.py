import os
import re
import json
from urllib.parse import urlparse
from functools import wraps
from crossref import restful as xref

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
        return f"{self.doi_reference.prefix}_{suffix}_{stem}"

    def get_pdf(self):
        return
        """
        Returns the path to the cached PDF, downloading it if necessary.
        """
        # Simulates downloading a PDF and saving it to the cache.
        # Placeholder: Add the actual download logic here
        with open(pdf_path, 'w') as f:
            f.write("This is a dummy PDF content for DOI: " + self.doi_reference.url)
        #print(f"Downloaded PDF for DOI {self.doi_reference.url} to {pdf_path}")

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

# Example usage
if __name__ == "__main__":
    from doi_model import ResearchDocument
    factory = DOIFactory()
    #doi_obj = factory.create_doi("https://doi.org/10.1101/2023.12.12.571258")
    #doi_obj = factory.create_doi("https://doi.org/10.1101/460345")
    #doi_obj = factory.create_doi("https://doi.org/10.1101/2022.04.21.488948")
    doi_obj = factory.create_doi("https://doi.org/10.1093/bioinformatics/btac729")
    pdf_path = doi_obj.get_pdf()
    #print(f"PDF cached at: {pdf_path}")
    import pprint
    pprint.pprint(doi_obj.xref)
    #print(f"Crossref data cached at: {crossref_path}")
    doc = ResearchDocument(**doi_obj.xref)
    #print(doc.json())
    #print(json.dumps(json.loads(doc.json())))
