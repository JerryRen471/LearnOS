from zhicore.chunking import chunk_document
from zhicore.types import Document


def test_chunk_document_with_overlap() -> None:
    text = "A" * 300 + "\n" + "B" * 300 + "\n" + "C" * 300
    document = Document(id="doc1", source="memory", text=text)
    chunks = chunk_document(document, chunk_size=400, overlap=80)

    assert len(chunks) >= 2
    assert chunks[0].start == 0
    assert chunks[1].start < chunks[0].end
    assert all(len(chunk.text) <= 400 for chunk in chunks)


def test_chunk_document_empty_text() -> None:
    document = Document(id="doc1", source="memory", text="  \n")
    chunks = chunk_document(document)
    assert chunks == []
