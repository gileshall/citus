import json
from datetime import datetime

def extract_doi_metadata(doi_metadata, default_value="NA"):
    extracted_data = {
        # Reference Count
        "reference_count": doi_metadata.get("reference-count", default_value),
        "is-referenced-by-count": doi_metadata.get("is-referenced-by-count", default_value),

        # Publisher Information
        "publisher": doi_metadata.get("publisher", default_value),
        "journal_title": doi_metadata.get("container-title", [default_value])[0] if doi_metadata.get("container-title", []) else default_value,

        # Funding Sources
        "funder_names": [funder.get("name", "Unknown funder") for funder in doi_metadata.get("funder", [])],
        "funder_awards": [award for funder in doi_metadata.get("funder", []) for award in funder.get("award", [])],
        "number_of_funders": len(doi_metadata.get("funder", [])),

        # Publication Date & Timeline
        "publication_year": doi_metadata.get("published", {}).get("date-parts", [[default_value]])[0][0] if doi_metadata.get("published", {}).get("date-parts", []) else default_value,
        "publication_month": doi_metadata.get("published", {}).get("date-parts", [[None, default_value]])[0][1] if doi_metadata.get("published", {}).get("date-parts", []) else default_value,

        # Licensing Information
        "licenses": list(set([license_info.get("URL", default_value) for license_info in doi_metadata.get("license", [])])),

        # Ethics and Declarations
        "ethics_declarations": [assertion.get("value", default_value) for assertion in doi_metadata.get("assertion", []) if assertion.get("group", {}).get("name") == "EthicsHeading"],

        # Authors Information
        "author_names": [f"{author.get('given', '')} {author.get('family', '')}".strip() if author.get('given') or author.get('family') else default_value for author in doi_metadata.get("author", [])],
        "author_orcids": [author.get("ORCID", default_value) for author in doi_metadata.get("author", [])],
        "author_count": len(doi_metadata.get("author", [])),

        # References with DOI Links
        "references_doi": [reference.get("DOI", default_value) for reference in doi_metadata.get("reference", []) if "DOI" in reference],

        # Boolean Fields
        "is_published_print": "published-print" in doi_metadata,
        "is_published_online": "published-online" in doi_metadata,

        # timestamp
        "_created_at": datetime.utcnow().isoformat()
    }

    return extracted_data
