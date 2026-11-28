"""Freeze all observed capture generations before default-off wire inspection."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path


def remember(probe, item, raw=None, entry=None, publication=None):
    if not hasattr(probe, 'private_generations'):
        probe.private_generations = []
    raw = raw if raw is not None else item['raw']
    record = {'sha256': hashlib.sha256(raw).hexdigest(), 'raw': raw,
              'id': (entry or {}).get('id', item.get('id')),
              'filename': (entry or {}).get('display_name', item.get('label', '') + '.' + item['format']),
              'anchors': [word for word in item.get('truth', {}).get('words', [])
                          if item.get('label', '') and item['label'] in word]}
    if publication:
        record.update(text=publication['text'], result_sha256=publication['result_sha256'])
    probe.private_generations.append(record)


def inspect_default_off(probe, observed):
    # This is only actual Local-process traffic to the configured Hub, not
    # local CLI-to-Local or Hub administrator-to-service control traffic.
    outgoing = [e for e in observed if e['kind'] == 'http-send' and e['owner'] == 'local'
                and e['host'] == '127.0.0.1' and e['port'] == probe.ports['hub']]
    generations = probe.private_generations
    filenames = {v['filename'] for v in generations}
    checked = []
    def inspect_names(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, str) and (key in {'filename', 'file_name', 'display_name', 'relative_path', 'path'}
                        or (key == 'name' and {'sha256', 'bytes'} <= value.keys())):
                    assert Path(item).name not in filenames, ('private document filename', key, item)
                inspect_names(item)
        elif isinstance(value, list):
            for item in value:
                inspect_names(item)
    for event in outgoing:
        wire = (probe.out / 'actual-outbound-http' / event['sha256']).read_bytes()
        assert len(wire) == event['bytes'] and hashlib.sha256(wire).hexdigest() == event['sha256']
        for record in generations:
            assert record['raw'] not in wire
            for field in ('sha256', 'id', 'result_sha256', 'text'):
                value = record.get(field)
                if value:
                    for representation in {value.encode(), json.dumps(value, ensure_ascii=True)[1:-1].encode(),
                                           json.dumps(value, ensure_ascii=False)[1:-1].encode()}:
                        assert representation not in wire, ('private generation field', field)
            for anchor in record['anchors']:
                assert anchor.encode() not in wire
        try:
            value = json.loads(wire)
        except (ValueError, UnicodeError):
            pass  # Headers/binary are still checked byte-for-byte above.
        else:
            inspect_names(value)
        checked.append({'sha256': event['sha256'], 'bytes': event['bytes'], 'pid': event['pid']})
    probe.save('lifecycle-default-off-all-generations', {'observed_local_to_hub_sends': checked,
        'generations': [{k: v for k, v in record.items() if k not in {'raw', 'text'}} for record in generations],
        'scope': 'All actual sends since process startup up to first project authorization; all captured generations and frozen native publication bodies, IDs, hashes and structured file names checked. Not an assertion about arbitrary possible text fragments.'})
    return outgoing
