



from __future__ import annotations

from typing import List
from pathlib import Path
import os
import re
import tempfile
from werkzeug.utils import secure_filename
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


_ARTIFACT_PATTERNS = [
    r"^\s*\d+\s*$",                          # lone page number line
    r"^\s*page\s+\d+\s*(of\s+\d+)?\s*$",     # "Page 3" / "Page 3 of 10"
    r"^[\s\-_=]{0,5}$",                      # blank or separator lines
]
_ARTIFACT_RE = re.compile("|".join(_ARTIFACT_PATTERNS), re.IGNORECASE)


def clean_text(text: str) -> str:
    replacements = {
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2014": "-", "\u2013": "-",
        "\u00a0": " ",
        "\u2022": "-",
        "\ufffd": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    lines = text.split("\n")
    cleaned_lines = [line for line in lines if not _ARTIFACT_RE.match(line)]

    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()


def clean_pdf(uploaded_files) -> List[Document]:
    """
    Load and clean a list of PDF file objects (from Flask request.files).

    Returns a flat list of Document objects, one per page, with metadata:
        - source: original filename
        - page: 0-based page number
    """
    documents: List[Document] = []

    for file in uploaded_files:
        if not file or not getattr(file, "filename", ""):
            continue

        filename = secure_filename(file.filename)
        if not filename.lower().endswith(".pdf"):
            continue

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                file.save(tmp)
                temp_path = tmp.name

            loader = PyPDFLoader(temp_path)
            pages = loader.load()

            for i, page in enumerate(pages):
                cleaned_text = clean_text(page.page_content)

                if not cleaned_text:
                    continue

                documents.append(
                    Document(
                        page_content=cleaned_text,
                        metadata={
                            "source": filename,
                            "page": i,
                        },
                    )
                )

        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    return documents



def test_pdf(pdf_path: str):
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()

    print(f"\nTotal pages: {len(pages)}\n")

    for i, page in enumerate(pages):
        cleaned_text = clean_text(page.page_content)

        print(f"\n--- Page {i + 1} ---")
        print(cleaned_text[:500])
        print("-" * 50)


if __name__ == "__main__":
    test_pdf("./pdf/myc.pdf")