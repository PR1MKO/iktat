import pytest

# Skip entire module if python-docx isn't available
docx = pytest.importorskip("docx")
from docx import Document


def test_docx_can_create_doc():
    d = Document()
    assert d is not None
