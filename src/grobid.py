#!/usr/bin/env python

from grobid_client import Client

from pathlib import Path
from grobid_client.api.pdf import process_fulltext_document
from grobid_client.models import Article, ProcessForm
from grobid_client.types import TEI, File


def pdf_to_tei_xml(pdf_path, tei_xml_path, figures=False):
    client = Client(base_url="http://localhost:8070/api", timeout=60)
    with open(pdf_path, "rb") as fh:
        payload = File(file_name=pdf_path, payload=fh, mime_type="application/pdf")
        form = ProcessForm(segment_sentences="1", input_=payload)
        resp = process_fulltext_document.sync_detailed(client=client, multipart_data=form)
        assert resp.is_success
        with open(tei_xml_path, "wb") as outfh:
            outfh.write(resp.content)
        article = TEI.parse(resp.content, figures=figures)

pdf_file = "/Users/ghall/Downloads/1-s2.0-S0010482524002737-main.pdf"
