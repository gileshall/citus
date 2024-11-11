from grobid_client.api.pdf import process_fulltext_document
from grobid_client.models import Article, ProcessForm
from grobid_client.types import TEI, File
from grobid_client import Client

def extract_text(pdf_path, output_path=None, figures=False):
    output_path = output_path or f'{pdf_path}.tei.xml'
    client = Client(base_url="http://localhost:8070/api", timeout=60)
    with open(pdf_path, "rb") as fh:
        payload = File(file_name=pdf_path, payload=fh, mime_type="application/pdf")
        form = ProcessForm(segment_sentences="1", input_=payload)
        resp = process_fulltext_document.sync_detailed(client=client, multipart_data=form)
        if not resp.is_success:
            msg = f"Grobid failed to extract text from {pdf_path} ({resp.content})"
            raise ValueError(msg)
        with open(output_path, "wb") as outfh:
            outfh.write(resp.content)
        return TEI.parse(resp.content, figures=figures)
