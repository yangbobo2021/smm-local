"""Deterministic BM25 over the two normally returned candidate sets."""
from collections import Counter
import copy
import math
from datetime import datetime, timezone

from .core import tokens


def merge_candidates(local, remote, query, limit):
    groups = {}
    for hit in [*local, *remote]:
        item = copy.deepcopy(hit)
        source = item.get("source")
        session = item.get("origin_session_key", item["source_session_id"])
        # A Hub's VibeInsight source identity is not the public short session ID.
        scope = item["archive_scope"]
        namespace = "agent" if source in {"codex", "claude-code"} else item.get("identity_namespace", scope)
        if not all(m.get("canonical_id") and m.get("content_version") for m in item["matched_messages"]):
            namespace = f"unverified:{scope}:{item['id']}"
        key = (namespace, source, session)
        group = groups.setdefault(key, {"hit": item, "messages": {}, "references": [], "identities": [], "supports": []})
        group["references"].append({"archive_scope": scope, "reference": item["reference"]})
        support = set()
        for message in item["matched_messages"]:
            identity = message.get("canonical_id")
            # Unverifiable copies are deliberately distinct.
            if not identity:
                identity = f"{scope}:{item.get('id')}:{message.get('position')}:{len(group['messages'])}"
            version = message.get("content_version")
            mkey = (identity, version)
            support.add(mkey)
            if mkey not in group["messages"]:
                group["messages"][mkey] = message
            else:
                old = group["messages"][mkey]
                origins = old.setdefault("origins", [])
                for origin in message.get("origins", []):
                    if origin not in origins:
                        origins.append(origin)
            group["identities"].append(identity)
        group["supports"].append((support, item))
    documents = []
    for key, group in groups.items():
        messages = list(group["messages"].values())
        messages.sort(key=lambda m: (m.get("source_order", m.get("position", 0)), m.get("timestamp") or "", m.get("canonical_id", "")))
        counts = Counter(tokens("\n".join(m["text"] for m in messages)))
        documents.append((key, group, messages, counts))
    if not documents:
        return []
    terms = set(tokens(query))
    frequency = Counter(term for _, _, _, counts in documents for term in terms if counts[term])
    average = max(1.0, sum(sum(counts.values()) for _, _, _, counts in documents) / len(documents))
    result = []
    for key, group, messages, counts in documents:
        length = sum(counts.values())
        score = 0.0
        for term in terms & counts.keys():
            idf = math.log1p((len(documents) - frequency[term] + .5) / (frequency[term] + .5))
            tf = counts[term]
            score += idf * tf * 2.2 / (tf + 1.2 * (.25 + .75 * length / average))
        if score <= 0:
            continue
        hit = group["hit"]
        complete = next((candidate for support, candidate in group["supports"] if support == set(group["messages"])), None)
        if complete is not None:
            hit = complete
        hit.update(matched_messages=messages, bm25_score=score, rerank_score=score,
                   origin_references=group["references"], needs_bundle=complete is None)
        latest = max((_time(m.get("timestamp")) for m in messages), default=float("-inf"))
        # Stable identity ordering is independent of which endpoint supplied it.
        stable = (key, tuple(sorted(set(group["identities"]))))
        result.append((score, latest, stable, hit))
    result.sort(key=lambda r: r[2])
    result.sort(key=lambda r: r[1], reverse=True)
    result.sort(key=lambda r: r[0], reverse=True)
    return [{**r[3], "rank": i} for i, r in enumerate(result[:limit], 1)]


def _time(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc).timestamp() if parsed.tzinfo is None else parsed.timestamp()
    except (AttributeError, ValueError, OverflowError):
        return float("-inf")
