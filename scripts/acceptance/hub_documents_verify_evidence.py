"""Verify public 007 evidence bytes; integrity is separate from acceptance."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(manifest_path, original_root=None):
    base = manifest_path.parent.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    seen = set()
    for row in manifest["files"]:
        relative = Path(row["public_path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        assert row["public_path"] not in seen
        seen.add(row["public_path"])
        public = base / relative
        assert not public.is_symlink() and public.resolve().is_relative_to(base)
        assert public.stat().st_size == row["bytes"], relative
        assert digest(public) == row["public_sha256"], relative
        if row["kind"].startswith("original"):
            assert row["original_sha256"] == row["public_sha256"], relative
        if original_root is not None:
            original = Path(row["original_locator"])
            assert original.resolve().is_relative_to(original_root.resolve())
            assert digest(original) == row["original_sha256"], relative
    index = json.loads((base / "acceptance-index.json").read_text(encoding="utf-8"))
    cases = index["cases"]
    assert index["case_count"] == 36
    assert len(cases) == 36 and len({c["case_id"] for c in cases}) == 36
    root = base.parents[2]
    for case in cases:
        if case["receipt"] is not None:
            receipt = case["receipt"]
            path = root / receipt["public_record"]
            assert path.resolve().is_relative_to(root)
            registered = json.loads(path.read_text(encoding="utf-8"))
            assert registered["result_sha256"] == receipt["receipt_sha256"]
            assert case["case_id"] in registered["case_ids"]
    return {
        "integrity": "passed",
        "public_files": len(seen),
        "originals_checked": original_root is not None,
        "case_count": len(cases),
        "acceptance_status_counts": dict(Counter(c["status"] for c in cases)),
        "integrity_does_not_mean_delivery_passed": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "changes/007-hub-document-search/evidence/public-manifest.json",
    )
    parser.add_argument("--original-root", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.manifest, args.original_root), ensure_ascii=False))


if __name__ == "__main__":
    main()
