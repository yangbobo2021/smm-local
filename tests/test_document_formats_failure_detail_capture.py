"""Real row replacement/closed details must not become a successful detail PNG."""
from copy import deepcopy
from html import escape
import json
import os
from pathlib import Path
import sys

import pytest

from document_helpers import observe
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/acceptance'))
from document_formats_lifecycle_visual import capture

pytestmark = pytest.mark.skipif(not (os.environ.get('SMM_008_TEST_BROWSER') or os.environ.get('PLAYWRIGHT_BROWSERS_PATH')),
    reason='requires explicitly prepared actual browser for screenshot-observer control')


def test_capture_reopens_actual_replacement_and_rejects_wrong_panel(tmp_path, monkeypatch):
    from playwright.sync_api import ElementHandle, sync_playwright
    entry = {'id': 'failure-detail-control', 'display_name': 'same.docx', 'version': 0, 'processing_version': 0,
        'published_snapshot': None, 'latest_attempt': {'capture_id': 'c', 'attempt_id': 'a', 'status': 'failed',
            'config_revision': 1, 'error': 'independent missing language'}, 'retry_target': {'capture_id': 'c'}}
    def markup(value):
        panels = ''.join('<pre data-native-detail="' + key + '">' + escape(json.dumps(value[key], ensure_ascii=False, indent=2)) + '</pre>'
                         for key in ('published_snapshot', 'latest_attempt', 'retry_target'))
        return '<div class="result"><p>same.docx · 文档 failure-detail-control · 格式 DOCX · 版本 0 · 处理版本 0 · failed</p><details><summary>详情</summary>' + panels + '</details></div>'
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True, **({'executable_path': os.environ['SMM_008_TEST_BROWSER']} if os.environ.get('SMM_008_TEST_BROWSER') else {}))
        try:
            page = browser.new_page()
            for owner, selector in [('local', 'doc-library-list'), ('hub', 'hub-library-list')]:
                page.set_content('<div id="' + selector + '">' + markup(entry) + '</div>')
                original, replaced = ElementHandle.screenshot, []
                def replaced_screenshot(handle, **options):
                    raw = original(handle, **options)
                    if not replaced:
                        handle.evaluate('row=>{const next=row.cloneNode(true);next.querySelector("details").open=false;row.replaceWith(next)}')
                        replaced.append(True)
                    return raw
                with monkeypatch.context() as patch:
                    patch.setattr(ElementHandle, 'screenshot', replaced_screenshot)
                    result = capture(page, owner, entry, 'docx', tmp_path / (owner + '.png'))
                assert len(result['rejected']) == 1 and result['after']['open']
                assert (tmp_path / result['rejected'][0]['file']).is_file()
                # A connected expanded row changing a value after real capture
                # must fail, even though another retry could display good data.
                page.set_content('<div id="' + selector + '">' + markup(entry) + '</div>')
                def wrong_screenshot(handle, **options):
                    raw = original(handle, **options)
                    handle.evaluate('row=>row.querySelector("[data-native-detail=retry_target]").textContent=JSON.stringify({capture_id:"foreign"})')
                    return raw
                with monkeypatch.context() as patch:
                    patch.setattr(ElementHandle, 'screenshot', wrong_screenshot)
                    with pytest.raises(AssertionError):capture(page, owner, entry, 'docx', tmp_path / (owner + '-wrong.png'))
                observe('actual-detail-capture-controls-' + owner, result)
        finally:browser.close()


def test_visible_table_checks_real_coordinates_spans_and_text(tmp_path):
    from playwright.sync_api import sync_playwright
    from types import SimpleNamespace
    from document_formats_lifecycle_readback import visible_table
    table = {'cells': [{'row': 1, 'column': 1, 'row_span': 1, 'column_span': 2, 'text': '独立表头'},
                       {'row': 2, 'column': 1, 'row_span': 1, 'column_span': 1, 'text': '73428'}]}
    markup = '<table><tbody id="hub-table-cells"><tr><td data-row="1" data-column="1" rowspan="1" colspan="2"><button data-cell-text>独立表头</button></td></tr><tr><td data-row="2" data-column="1" rowspan="1" colspan="1"><button data-cell-text>73428</button></td></tr></tbody></table>'
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True, **({'executable_path': os.environ['SMM_008_TEST_BROWSER']} if os.environ.get('SMM_008_TEST_BROWSER') else {}))
        try:
            page = browser.new_page()
            probe = SimpleNamespace(page=page, prefix='hub')
            page.set_content(markup)
            visible_table(probe, table)
            for script in [
                'document.querySelectorAll("[data-row]")[1].remove()',
                'document.querySelectorAll("[data-row]")[1].dataset.column="2"',
                'document.querySelectorAll("[data-row]")[0].colSpan=1',
                'document.querySelectorAll("[data-row]")[1].querySelector("button").textContent="foreign"',
            ]:
                page.set_content(markup)
                page.evaluate(script)
                with pytest.raises(AssertionError):visible_table(probe, table)
            page.screenshot(path=str(tmp_path/'actual-render-control.png'))
        finally:browser.close()
