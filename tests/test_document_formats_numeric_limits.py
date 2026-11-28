"""Literal SPEC B9 boundaries, using real source/serialized bytes."""
from io import BytesIO
import gzip
import hashlib
import json
from zipfile import ZipFile, ZIP_DEFLATED

import pytest

from document_helpers import observe
from document_formats_managed_empty_fixture import blank_original
from document_formats_pdf_security_fixture import content_pdf
from document_formats_table_fixture import workbook
from test_document_formats_retry import keep


def archive_with_parts(parts):
    stream = BytesIO()
    with ZipFile(stream, 'w', ZIP_DEFLATED) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    return stream.getvalue()


def blank_parts():
    with ZipFile(BytesIO(blank_original('docx', 'numeric limits'))) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def test_opc_actual_member_count_accepts_10000_and_rejects_10001():
    from smm_local.document_formats.ooxml import Package
    parts = blank_parts()
    for number in range(10000 - len(parts)):
        parts['opaque/member' + str(number) + '.bin'] = b'x'
    assert len(parts) == 10000
    raw = archive_with_parts(parts)
    keep('numeric/opc-exactly-10000.docx', raw)
    accepted = Package(raw, 'docx')
    assert set(accepted.files) == set(parts) and accepted.expanded_bytes == sum(map(len, parts.values()))
    parts['opaque/one-more.bin'] = b'x'
    raw = archive_with_parts(parts)
    keep('numeric/opc-10001.docx', raw)
    with pytest.raises(ValueError, match='10000'):
        Package(raw, 'docx')


def test_opc_actual_expansion_accepts_100mib_and_rejects_one_more_byte():
    from smm_local.document_formats.ooxml import Package
    parts = blank_parts()
    parts['opaque/payload.bin'] = b'x' * (100 * 1024 * 1024 - sum(map(len, parts.values())))
    raw = archive_with_parts(parts)
    assert len(raw) < 20 * 1024 * 1024
    keep('numeric/opc-expands-to-exactly-100MiB.docx', raw)
    accepted = Package(raw, 'docx')
    assert accepted.expanded_bytes == sum(map(len, parts.values())) == 100 * 1024 * 1024
    assert accepted.files['opaque/payload.bin'] == parts['opaque/payload.bin']
    parts['opaque/payload.bin'] += b'y'
    raw = archive_with_parts(parts)
    keep('numeric/opc-expands-to-100MiB-plus-one.docx', raw)
    with pytest.raises(ValueError, match='100MiB'):
        Package(raw, 'docx')


def test_normalized_unicode_text_accepts_exactly_8mib_and_rejects_one_byte_more():
    from smm_local.document_results import Builder
    size = 8 * 1024 * 1024
    text = '中' * (size // 3) + 'a' * (size % 3)
    assert len(text.encode('utf-8')) == size
    builder = Builder('docx', hashlib.sha256(b'independent raw').hexdigest(), {})
    builder.add(text, {'part': 'word/document.xml', 'path': 'body/paragraph[1]'})
    result = builder.finish()
    assert result['text'] == text and result['text_sha256'] == hashlib.sha256(text.encode('utf-8')).hexdigest()
    wire = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    keep('numeric/exact-8MiB-result.json.gz', gzip.compress(wire, mtime=0))
    other = Builder('docx', hashlib.sha256(b'independent raw').hexdigest(), {})
    with pytest.raises(ValueError, match='8MiB'):
        other.add(text + 'b', {'part': 'word/document.xml', 'path': 'body/paragraph[1]'})
    observe('literal-text-boundary', {'accepted_utf8_bytes': size, 'rejected_utf8_bytes': size + 1,
                                    'accepted_codepoints': len(text), 'result_sha256': hashlib.sha256(wire).hexdigest()})


def test_complete_serialized_result_accepts_16mib_and_rejects_one_byte_more():
    from smm_local.document_results import Builder, validate
    base = Builder('docx', hashlib.sha256(b'independent raw').hexdigest(), {'padding': ''}).finish()
    encode = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    size = 16 * 1024 * 1024
    base['profile']['padding'] = 'x' * (size - len(encode(base)))
    wire = encode(base)
    assert len(wire) == size
    assert validate(base) == base
    keep('numeric/exact-16MiB-result.json.gz', gzip.compress(wire, mtime=0))
    base['profile']['padding'] += 'y'
    assert len(encode(base)) == size + 1
    with pytest.raises(ValueError, match='16MiB'):
        validate(base)
    observe('literal-result-boundary', {'accepted_bytes': size, 'rejected_bytes': size + 1,
                                      'accepted_sha256': hashlib.sha256(wire).hexdigest()})


def test_xlsx_real_sheet_count_accepts_64_and_rejects_65():
    from smm_local.document_formats.spreadsheet import parse
    sheets = [{'name': 'Sheet' + str(number), 'cells': [{'row': 1, 'column': 1, 'text': 'VALUE' + str(number)}]}
              for number in range(1, 65)]
    raw, _ = workbook(sheets)
    keep('numeric/exactly-64-sheets.xlsx', raw)
    result = parse(raw, hashlib.sha256(raw).hexdigest(), {})
    assert len(result['tables']) == 64
    assert [table['location']['sheet'] for table in result['tables']] == [sheet['name'] for sheet in sheets]
    assert [table['cells'][0]['text'] for table in result['tables']] == ['VALUE' + str(n) for n in range(1, 65)]
    sheets.append({'name': 'Sheet65', 'cells': [{'row': 1, 'column': 1, 'text': 'VALUE65'}]})
    raw, _ = workbook(sheets)
    keep('numeric/65-sheets.xlsx', raw)
    with pytest.raises(ValueError, match='64'):
        parse(raw, hashlib.sha256(raw).hexdigest(), {})


def test_pdf_real_page_tree_accepts_200_and_rejects_201(tmp_path):
    from smm_local.document_formats.pdf_guard import intermediate
    import pypdfium2
    raw = content_pdf([], [[] for _ in range(200)])
    keep('numeric/exactly-200-pages.pdf', raw)
    output = tmp_path / 'accepted.pdf'
    result = intermediate(raw, output)
    assert result['pages'] == 200
    with pypdfium2.PdfDocument(output) as document:
        assert len(document) == 200
    raw = content_pdf([], [[] for _ in range(201)])
    keep('numeric/201-pages.pdf', raw)
    rejected = tmp_path / 'rejected.pdf'
    with pytest.raises(ValueError, match='200'):
        intermediate(raw, rejected)
    assert not rejected.exists()
