import sys
import xml.etree.ElementTree as ET

# Define the TEI namespace
ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

# Define default sections order
DEFAULT_SECTIONS_ORDER = (
  'title', 'authors', 'abstract',
  'body', 'references', 'funding',
  'publisher', 'license',
  'data_sources', 'article_status'
)

def get_title(root):
    title = root.find('.//tei:titleStmt/tei:title[@type="main"]', ns)
    return f"# {title.text.strip()}\n" if title is not None and title.text else "# Untitled\n\n"

def get_authors(root):
    output = "## Authors\n\n"
    authors = root.findall('.//tei:sourceDesc//tei:analytic//tei:author', ns)
    if authors:
        for author in authors:
            pers_name = author.find('tei:persName', ns)
            if pers_name is None:
                continue

            first_name = pers_name.find('tei:forename[@type="first"]', ns)
            first_name_text = first_name.text if first_name is not None else ""
            
            middle_name = pers_name.find('tei:forename[@type="middle"]', ns)
            middle_name_text = middle_name.text if middle_name is not None else ""
            
            last_name = pers_name.find('tei:surname', ns)
            last_name_text = last_name.text if last_name is not None else ""
            
            author_name = f"**{first_name_text} {middle_name_text} {last_name_text}**".strip()

            affiliation_info = ""
            affiliation = author.find('tei:affiliation', ns)
            if affiliation is not None:
                dept = affiliation.find('tei:orgName[@type="department"]', ns)
                institution = affiliation.find('tei:orgName[@type="institution"]', ns)
                country = affiliation.find('tei:address/tei:country', ns)
                
                dept_text = dept.text if dept is not None else ""
                institution_text = institution.text if institution is not None else ""
                country_text = country.text if country is not None else ""
                
                affiliation_info = f", {dept_text}, {institution_text}, {country_text}".strip(", ")

            email = author.find('tei:email', ns)
            email_text = f", Email: {email.text}" if email is not None else ""
            
            output += f"- {author_name}{affiliation_info}{email_text}\n"
        return output + "\n"
    return ""

def get_abstract(root):
    abstract = root.find('.//tei:profileDesc/tei:abstract', ns)
    if abstract is not None:
        abstract_text = ""
        for element in abstract.iter():
            if element.tag == f"{{{ns['tei']}}}ref":
                ref_content = element.text if element.text else ""
                abstract_text += ref_content
            elif element.text:
                abstract_text += element.text
            if element.tail:
                abstract_text += element.tail
        return f"## Abstract\n\n{abstract_text.strip()}\n\n"
    return ""

def get_body(root):
    output = "## Body\n\n"
    body = root.find('.//tei:text/tei:body', ns)
    if body is not None:
        for div in body.findall('tei:div', ns):
            section_title = div.find('tei:head', ns)
            if section_title is not None and section_title.text:
                output += f"### {section_title.text.strip()}\n\n"

            for paragraph in div.findall('tei:p', ns):
                paragraph_text = ""
                for element in paragraph.iter():
                    if element.tag == f"{{{ns['tei']}}}ref":
                        ref_content = element.text if element.text else ""
                        paragraph_text += ref_content
                    elif element.text:
                        paragraph_text += element.text
                    if element.tail:
                        paragraph_text += element.tail
                output += paragraph_text.strip() + "\n\n"
        return output + "\n"
    return ""

def get_references(root):
    output = "## References\n\n"
    references = root.findall('.//tei:listBibl/tei:biblStruct', ns)
    for idx, ref in enumerate(references, start=1):
        title = ref.find('.//tei:title', ns)
        title_text = title.text if title is not None else "Untitled"

        authors = ref.findall('.//tei:author/tei:persName', ns)
        author_names = []
        for author in authors:
            first_name = author.find('tei:forename[@type="first"]', ns)
            first_name_text = first_name.text if first_name is not None else ""
            
            middle_name = author.find('tei:forename[@type="middle"]', ns)
            middle_name_text = middle_name.text if middle_name is not None else ""
            
            last_name = author.find('tei:surname', ns)
            last_name_text = last_name.text if last_name is not None else ""
            
            author_names.append(f"{first_name_text} {middle_name_text} {last_name_text}".strip())
        
        authors_text = ", ".join(author_names) if author_names else "Unknown authors"
        
        journal = ref.find('.//tei:title[@level="j"]', ns)
        journal_text = journal.text if journal is not None else "Unknown journal"

        date = ref.find('.//tei:date[@type="published"]', ns)
        date_text = date.get('when') if date is not None else "Unknown date"

        page_from = ref.find('.//tei:biblScope[@unit="page"][@from]', ns)
        page_to = ref.find('.//tei:biblScope[@unit="page"][@to]', ns)
        pages_text = f"pp. {page_from.text}-{page_to.text}" if page_from is not None and page_to is not None else f"p. {page_from.text}" if page_from is not None else ""

        output += f"{idx}. {authors_text}. *\"{title_text}\"*. {journal_text}, {date_text}, {pages_text}\n"
    return output + "\n"

def get_funding(root):
    output = "## Funding Sources\n\n"
    funders = root.findall('.//tei:funder/tei:orgName[@type="full"]', ns)
    for funder in funders:
        output += f"- {funder.text}\n"
    return output + "\n" if funders else ""

def get_publisher(root):
    publisher = root.find('.//tei:publicationStmt/tei:publisher', ns)
    return f"## Publisher\n\n{publisher.text}\n\n" if publisher is not None and publisher.text else ""

def get_license(root):
    availability = root.find('.//tei:publicationStmt/tei:availability[@status]', ns)
    status = availability.get('status') if availability is not None else "unknown"
    return f"## License\n\n**Status:** {status}\n\n"

def get_data_sources(root):
    data_availability = root.find('.//tei:back//tei:div[@type="availability"]/tei:p', ns)
    if data_availability is not None and data_availability.text:
        return f"## Data Sources\n\n{data_availability.text.strip()}\n\n"
    return ""

def get_article_status(root):
    status = root.find('.//tei:sourceDesc/tei:biblStruct/tei:note[@type="submission"]', ns)
    return f"## Article Status\n\n{status.text.strip()}\n\n" if status is not None and status.text else ""

SECTION_FUNCTIONS = {
    'title': get_title,
    'authors': get_authors,
    'abstract': get_abstract,
    'body': get_body,
    'references': get_references,
    'funding': get_funding,
    'publisher': get_publisher,
    'license': get_license,
    'data_sources': get_data_sources,
    'article_status': get_article_status,
}

def convert_tei_to_text(file_path, output_path=None, sections_order=None):
    sections_order = sections_order or DEFAULT_SECTIONS_ORDER

    # Ensure all requested sections are recognized
    for section in sections_order:
        if section not in SECTION_FUNCTIONS:
            raise ValueError(f"Unknown section: {section}")

    output_path = output_path or f"{file_path}.txt"

    # Parse the XML file
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Collect all requested sections
    output = ""
    for section in sections_order:
        output += SECTION_FUNCTIONS[section](root)
    
    with open(output_path, 'w') as fh:
        fh.write(output)

    return output

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_tei_full_text.py <filename>")
    else:
        file_path = sys.argv[1]
        txt = convert_tei_to_text(file_path)
        print(txt)
