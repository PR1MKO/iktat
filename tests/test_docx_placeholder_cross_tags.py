import tempfile
import zipfile
from pathlib import Path

from app.investigations.routes import _normalize_xml_placeholders, _render_docx_template

# Placeholder split across <w:t>, <w:r>, and even paragraph boundaries.
SPLIT_ACROSS_TAGS = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:r><w:t>{{ti</w:t></w:r>
      <w:r><w:t>tul</w:t></w:r>
      <w:r><w:t>us}}</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>{{viz</w:t></w:r></w:p>
    <w:p>
      <w:r><w:t>sg_</w:t></w:r>
      <w:r><w:t>date}}</w:t></w:r>
    </w:p>
  </w:body>
</w:document>"""


def test_normalize_xml_placeholders_crosses_any_tags():
    out, changed = _normalize_xml_placeholders(SPLIT_ACROSS_TAGS)
    s = out.decode("utf-8")
    assert changed is True
    assert "{{titulus}}" in s
    assert "{{vizsg_date}}" in s


def _make_docx(xml_bytes: bytes) -> Path:
    tmp = tempfile.NamedTemporaryFile(prefix="tpl_", suffix=".docx", delete=False)
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", xml_bytes)
        z.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
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
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>""",
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


def test_render_replaces_values_when_split_across_tags(tmp_path):
    docx = _make_docx(SPLIT_ACROSS_TAGS)
    out = tmp_path / "out.docx"
    context = {"titulus": "Dr.", "vizsg_date": "2025-09-24 10:30"}
    _render_docx_template(docx, out, context)
    with zipfile.ZipFile(out, "r") as z:
        data = z.read("word/document.xml").decode("utf-8")
        assert "Dr." in data
        assert "2025-09-24 10:30" in data
        assert "{{" not in data  # ensure placeholders were consumed
