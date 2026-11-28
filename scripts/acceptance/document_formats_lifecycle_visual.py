"""Bind a failure-details screenshot to the same visible expanded row handle."""
from __future__ import annotations
import json
import time

STATE = '''row=>{const box=row.getBoundingClientRect();return {
 connected:row.isConnected,open:row.querySelector('details')?.open,text:row.innerText,
 x:box.x+scrollX,y:box.y+scrollY,width:box.width,height:box.height,
 fields:Object.fromEntries([...row.querySelectorAll('[data-native-detail]')]
 .map(node=>[node.dataset.nativeDetail,node.textContent]))}}'''


def capture(page, owner, entry, format, path):
    from playwright.sync_api import Error
    from test_document_formats_web_uploads import assert_ui_snapshot
    deadline, rejected = time.monotonic() + 20, []
    expected = {key: entry[key] for key in ('published_snapshot', 'latest_attempt', 'retry_target')}
    expected['latest_attempt'] = {key: entry['latest_attempt'][key]
        for key in ('capture_id', 'attempt_id', 'status', 'config_revision', 'error')}
    def check(value):
        actual = {key: json.loads(value['fields'][key]) for key in expected}
        assert actual == expected, actual
    while True:
        assert time.monotonic() < deadline, 'Expanded details did not remain stable for capture'
        row = assert_ui_snapshot(page, owner, entry, format)
        handle = row.element_handle(timeout=max(1, int((deadline-time.monotonic())*1000)))
        assert handle is not None
        try:
            before = handle.evaluate(STATE)
            if not before['connected'] or not before['open']:continue
            check(before)
            try:
                handle.screenshot(path=str(path), timeout=max(1, int((deadline-time.monotonic())*1000)))
            except Error:
                state = handle.evaluate(STATE)
                if not state['connected'] or not state['open']:continue
                raise
            after = handle.evaluate(STATE)
            if after['connected'] and after['open']:
                check(after)  # Wrong values are failures, never retryable.
                if all(abs(before[k]-after[k]) <= .5 for k in ('x', 'y', 'width', 'height')):
                    return {'before': before, 'after': after, 'rejected': rejected}
            saved = path.with_name(path.stem + '.rejected-' + str(len(rejected)+1) + path.suffix)
            path.replace(saved)
            rejected.append({'file': saved.name, 'before': before, 'after': after})
        finally:
            handle.dispose()
