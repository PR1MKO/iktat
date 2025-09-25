import tempfile
import zipfile
from pathlib import Path

from app.investigations.routes import (
    _normalize_xml_placeholders,
    _sanitize_docx_placeholders,
)

BROKEN_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Külső ügyirat: </w:t><w:t>{{kulso</w:t><w:t xml:space="preserve"> ugyirat}}</w:t></w:r></w:p>
    <w:p><w:r><w:t>Iktatási: </w:t><w:t>{{iktatasi</w:t><w:t xml:space="preserve"> szam}}</w:t></w:r></w:p>
    <w:p><w:r><w:t>Jegyzőkönyv: </w:t><w:t>{{jkv.vezető}}</w:t></w:r></w:p>
  </w:body>
</w:document>""".encode(
    "utf-8"
)


def _make_fake_docx(xml_bytes: bytes) -> Path:
    tmp = tempfile.NamedTemporaryFile(prefix="fake_doc_", suffix=".docx", delete=False)
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", xml_bytes)
        z.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        z.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>""",
        )
        z.writestr(
            "word/_rels/document.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>""",
        )
        z.writestr(
            "docProps/core.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>Fixture</dc:title>
</cp:coreProperties>""",
        )
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def test_normalize_xml_placeholders_merges_runs_and_sanitizes_names():
    output, changed = _normalize_xml_placeholders(BROKEN_XML)
    assert changed is True
    text = output.decode("utf-8")
    assert "{{kulsougyirat}}" in text
    assert "{{iktatasiszam}}" in text
    assert "{{jkvvezeto}}" in text


def test_sanitize_docx_placeholders_returns_tempfile_with_normalized_content():
    docx_path = _make_fake_docx(BROKEN_XML)
    sanitized_path = _sanitize_docx_placeholders(docx_path)
    assert sanitized_path.exists()
    with zipfile.ZipFile(sanitized_path, "r") as z:
        data = z.read("word/document.xml").decode("utf-8")
        assert "{{kulsougyirat}}" in data
        assert "{{iktatasiszam}}" in data
        assert "{{jkvvezeto}}" in data
    sanitized_path.unlink()
    docx_path.unlink()
