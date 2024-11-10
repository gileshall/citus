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
            self._postfix = doi_input._postfix
        else:
            self.doi_input = doi_input
            self._prefix, self._postfix = self._parse_doi(doi_input)

    def _parse_doi(self, doi_input):
        """
        Parse the input to extract prefix and postfix.
        """
        if '/' in doi_input:
            if doi_input.startswith('https://doi.org/'):
                doi_input = doi_input[len('https://doi.org/'):]
            parts = doi_input.split('/')
            if len(parts) == 2:
                return parts[0], parts[1]
            else:
                raise ValueError("Invalid DOI format")
        else:
            raise ValueError("Invalid DOI input, must contain '/' to separate prefix and postfix")

    @property
    def url(self):
        """
        Construct the full DOI URL from prefix and postfix.
        """
        return f"https://doi.org/{self._prefix}/{self._postfix}"

    @property
    def prefix(self):
        return self._prefix

    @property
    def postfix(self):
        return self._postfix


def cache_result(filename_template):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            filename = filename_template.format(
                prefix=self.doi_reference.prefix,
                postfix=self.doi_reference.postfix
            )
            cache_path = os.path.join(self.cache_path, filename)
            if not os.path.exists(cache_path):
                func(self, cache_path, *args, **kwargs)
            return cache_path
        return wrapper
    return decorator


class DOI:
    def __init__(self, cache_path, doi_reference):
        if not isinstance(doi_reference, DOIReference):
            doi_reference = DOIReference(doi_reference)
        self.doi_reference = doi_reference
        self.cache_path = cache_path

        # Create directory if it does not exist
        if not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)

    @cache_result("{prefix}_{postfix}.pdf")
    def get_pdf(self, pdf_path):
        """
        Returns the path to the cached PDF, downloading it if necessary.
        """
        # Simulates downloading a PDF and saving it to the cache.
        # Placeholder: Add the actual download logic here
        with open(pdf_path, 'w') as f:
            f.write("This is a dummy PDF content for DOI: " + self.doi_reference.url)
        #print(f"Downloaded PDF for DOI {self.doi_reference.url} to {pdf_path}")

    @cache_result("{prefix}_{postfix}_crossref.json")
    def get_crossref_data(self, json_path):
        """
        Returns the path to the cached Crossref data, downloading it if necessary.
        """
        work = xref.Works()
        info = work.doi(self.doi_reference.url)
        with open(json_path, 'w') as fh:
            json.dump(info, fh, indent=2)
        #print(f"Downloaded Crossref data for DOI {self.doi_reference.url} to {json_path}")

    # Additional cacheable methods can be added here, e.g., get_ascii_text(), get_metadata(), etc.


class DOIFactory:
    def __init__(self, base_path='./doi-cache'):
        self.base_path = base_path
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)

    def create_doi(self, doi_input):
        """
        Create a DOI object with a cache path based on the given DOI input.
        """
        doi_reference = DOIReference(doi_input)
        cache_dir = self._get_cache_directory(doi_reference)
        return DOI(cache_path=cache_dir, doi_reference=doi_reference)

    def _get_cache_directory(self, doi_reference):
        """
        Construct the cache directory based on the DOI.
        """
        return os.path.join(self.base_path, doi_reference.prefix, doi_reference.postfix)


# Example usage
if __name__ == "__main__":
    from doi_model import ResearchDocument
    factory = DOIFactory()
    #doi_obj = factory.create_doi("https://doi.org/10.1101/2023.12.12.571258")
    doi_obj = factory.create_doi("https://doi.org/10.1101/460345")
    pdf_path = doi_obj.get_pdf()
    #print(f"PDF cached at: {pdf_path}")
    crossref_path = doi_obj.get_crossref_data()
    #print(f"Crossref data cached at: {crossref_path}")
    with open(crossref_path) as fh:
        obj = json.load(fh)
    doc = ResearchDocument(**obj)
    print(json.dumps(json.loads(doc.json())))
