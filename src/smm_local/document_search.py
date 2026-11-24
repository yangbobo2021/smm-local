"""One signed project range, bounded candidates, local ranking and exact routing."""

from __future__ import annotations
from collections import Counter
import math
import sqlite3
from .core import tokens
from .documents import Documents
from . import references, federation
from .document_protocol import integer, identity


def _origin(db, config, hit):
    return {
        "device_id": config["device_id"] if config else references.material(db)[0],
        "archive_id": references.material(db)[0],
        "document_id": hit["id"],
    }


def _identity(hit):
    origin = hit["origin"]
    return tuple(origin[k] for k in ("device_id", "archive_id", "document_id")) + (
        hit["version"],
    )


def _local(db, config, options, query):
    result = Documents(db).search(query, **options)
    for hit in result["results"]:
        hit.update(
            origin=_origin(db, config, hit),
            archive_scope="local",
            origin_kind="local",
            device_name=(config or {}).get("device_name", "本机"),
            origin_references=[
                {"archive_scope": "local", "reference": hit["reference"]}
            ],
        )
    return result


def _scope(db, config, info, project_id, hub_project_id):
    body = {"hub_id": info["hub_id"], "device_id": config["device_id"]}
    if hub_project_id is not None:
        body["hub_project_id"] = hub_project_id
    else:
        federation._push_projects(db, config, info["hub_id"], 0)
        body["project_id"] = federation._remote_project_key(db, project_id)
    response = federation._request(config, "/query-scope", body)
    if hub_project_id is None:
        return federation._validated_scope(
            response, info["hub_id"], config["device_id"], body["project_id"]
        )
    try:
        payload = references.routing_metadata(response["scope_reference"])
        projects = response["effective_projects"]
        if (
            response["hub_id"] != info["hub_id"]
            or payload.get("kind") != "query_scope"
            or payload.get("hub_id") != info["hub_id"]
            or payload.get("device_id") != config["device_id"]
            or payload.get("hub_project_id") != hub_project_id
            or payload.get("projects") != projects
            or not any(p["id"] == hub_project_id for p in projects)
        ):
            raise ValueError()
        if any(
            type(p["id"]) is not int
            or not all(
                isinstance(p[k], str) and p[k]
                for k in ("source", "owner", "source_key", "name")
            )
            for p in projects
        ):
            raise ValueError()
        return response
    except (ValueError, KeyError, TypeError) as exc:
        raise federation.HubUnavailable("Hub根项目范围无效") from exc


def search(
    db,
    query,
    *,
    scope="all",
    project_id=None,
    hub_project_id=None,
    limit=5,
    local=False,
):
    integer(limit, "limit")
    if (
        limit > 50
        or type(local) is not bool
        or scope not in {"all", "project"}
        or not isinstance(query, str)
        or not tokens(query)
    ):
        raise ValueError("检索范围、查询或limit无效")
    if project_id is not None:
        integer(project_id, "本机项目ID")
        db.effective_projects(project_id)
    if hub_project_id is not None:
        integer(hub_project_id, "Hub项目ID")
    if (
        (project_id is not None and hub_project_id is not None)
        or (scope == "all" and (project_id is not None or hub_project_id is not None))
        or (scope == "project" and project_id is None and hub_project_id is None)
        or (local and hub_project_id is not None)
    ):
        raise ValueError("须明确选择一个本机或Hub项目根；Hub根不能只查本机")
    config = federation.hub_config(db)
    options = {"scope": scope, "project_id": project_id, "limit": limit}
    snapshot = None
    remote = None
    reason = None
    hub_coverage = "not_requested"
    failures = []
    info = None
    if hub_project_id is not None:
        options = {"scope": "all", "exact_project_ids": [], "limit": limit}
    if config and not local:
        hub_coverage = "unavailable"
        try:
            info = federation._hub_info(config)
            if not any(
                c.startswith("documents-") for c in info.get("capabilities", [])
            ):
                hub_coverage = "unsupported"
                raise federation.HubUnavailable("当前Hub不支持文档检索")
            context = {
                "hub_id": info["hub_id"],
                "document_epoch": info["document_epoch"],
            }
            payload = {**context, "query": query, "limit": limit}
            if scope == "project":
                snapshot = _scope(db, config, info, project_id, hub_project_id)
                keys = {p["stable_key"]: p["id"] for p in db.projects()}
                exact = sorted(
                    {
                        keys[p["source_key"]]
                        for p in snapshot["effective_projects"]
                        if p["source"] == "device"
                        and p["owner"] == config["device_id"]
                        and p["source_key"] in keys
                    }
                )
                options = {"scope": "all", "exact_project_ids": exact, "limit": limit}
                payload.update(
                    scope_reference=snapshot["scope_reference"],
                    device_id=config["device_id"],
                )
            remote = federation._request(config, "/documents/search", payload)
            if (
                remote.get("hub_id") != info["hub_id"]
                or remote.get("document_epoch") != info["document_epoch"]
                or not isinstance(remote.get("results"), list)
                or len(remote["results"]) > limit
            ):
                raise federation.HubUnavailable("Hub文档响应无效")
            valid = []
            for hit in remote["results"]:
                try:
                    ref = references.routing_metadata(hit["reference"])
                    origin = hit["origin"]
                    for key in ("device_id", "archive_id", "document_id"):
                        identity(origin[key])
                    integer(hit["version"])
                    integer(hit["text_length"], minimum=0)
                    if (
                        ref.get("kind") != "hub_document"
                        or any(ref.get(k) != v for k, v in context.items())
                        or ref.get("origin") != origin
                        or any(
                            ref.get(k) != hit.get(k)
                            for k in ("version", "sha256", "text_sha256", "text_length")
                        )
                    ):
                        raise ValueError()
                    if (
                        not isinstance(hit["text"], str)
                        or len(hit["text"]) > 2000
                        or type(hit["start"]) is not int
                        or type(hit["end"]) is not int
                        or not 0 <= hit["start"] < hit["end"] <= hit["text_length"]
                        or len(hit["text"]) != hit["end"] - hit["start"]
                    ):
                        raise ValueError()
                    original = hit["reference"]
                    hit["origin_references"] = [
                        {"archive_scope": "hub", "reference": original}
                    ]
                    hit["reference"] = references.wrap_hub(db, info["hub_id"], original)
                    hit["archive_scope"] = "hub"
                    valid.append(hit)
                except (ValueError, KeyError, TypeError):
                    failures.append("Hub文档候选身份、版本、摘要或片段无效，已排除")
            remote["results"] = valid
            hub_coverage = "partial" if failures else "complete"
        except (federation.HubUnavailable, KeyError, ValueError) as exc:
            reason = str(exc)
            remote = None
            if snapshot is not None and getattr(exc, "status", None) in {400, 409, 422}:
                snapshot = None
            if scope == "project" and snapshot is None:
                options = {
                    "scope": "all",
                    "exact_project_ids": [project_id] if project_id is not None else [],
                    "limit": limit,
                }
    elif hub_project_id is not None:
        reason = "未连接Hub，无法确定Hub根项目范围"
        hub_coverage = "unavailable"
    local_coverage = "complete"
    try:
        local_result = _local(db, config, options, query)
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        if remote is None:
            raise
        local_result = {"results": []}
        local_coverage = "partial"
        failures.append(str(exc))
    if local or not config:
        # Explicit Local and standalone operation retain 006's normal lexical
        # ordering; candidate-union reranking belongs to the federated path.
        return {
            **local_result,
            "scope": scope,
            "requested_scope": scope,
            "archive_scope": "local",
            "effective_projects": [],
            "coverage": {
                **local_result.get("coverage", {}),
                "local": local_coverage,
                "hub": hub_coverage,
            },
            "fallback_reason": reason,
            "candidate_failures": failures,
        }
    candidates = {}
    for hit in local_result["results"] + (remote["results"] if remote else []):
        key = _identity(hit)
        if key in candidates:
            old = candidates[key]
            if any(
                old.get(k) != hit.get(k)
                for k in ("sha256", "text_sha256", "text_length")
            ):
                failures.append("同一身份和版本的文档摘要冲突，排除远端候选")
                hub_coverage = "partial"
                continue
            start = max(old["start"], hit["start"])
            end = min(old["end"], hit["end"])
            if start < end and (
                old["text"][start - old["start"] : end - old["start"]]
                != hit["text"][start - hit["start"] : end - hit["start"]]
            ):
                failures.append("同一身份和版本的文档片段冲突，排除远端候选")
                hub_coverage = "partial"
                continue
            parts = [old["reference"], hit["reference"]]
            hit["reference"] = references.bundle(db, parts)
            hit["archive_scope"] = "combined"
            hit["origin_references"] = (
                old["origin_references"] + hit["origin_references"]
            )
        candidates[key] = hit
    counts = {key: Counter(tokens(hit["text"])) for key, hit in candidates.items()}
    n = len(counts)
    avg = max(1, sum(sum(c.values()) for c in counts.values()) / max(n, 1))
    terms = list(dict.fromkeys(tokens(query)))
    for key, hit in candidates.items():
        c = counts[key]
        score = 0
        for term in terms:
            tf = c[term]
            df = sum(term in values for values in counts.values())
            if tf:
                score += (
                    math.log1p((n - df + 0.5) / (df + 0.5))
                    * tf
                    * 2.2
                    / (tf + 1.2 * (0.25 + 0.75 * sum(c.values()) / avg))
                )
        hit["rerank_score"] = score
    hits = sorted(
        candidates.values(), key=lambda hit: (-hit["rerank_score"], _identity(hit))
    )[:limit]
    for index, hit in enumerate(hits, 1):
        hit["rank"] = index
    return {
        **local_result,
        "results": hits,
        "scope": scope,
        "requested_scope": scope,
        "archive_scope": "combined" if remote is not None else "local",
        "effective_projects": snapshot["effective_projects"] if snapshot else [],
        "coverage": {
            **local_result.get("coverage", {}),
            "local": local_coverage,
            "hub": hub_coverage,
            "hub_sources": (
                remote.get("coverage", {}).get("sources", []) if remote else []
            ),
        },
        "fallback_reason": reason,
        "candidate_failures": failures,
    }


def read(db, reference, *, start=None, end=None):
    payload = references.decode(db, reference)
    kind = payload.get("kind")
    if kind == "document":
        value = Documents(db).read(reference, start=start, end=end)
        config = federation.hub_config(db)
        return {
            **value,
            "archive_scope": "local",
            "origin": _origin(db, config, value),
            "origin_kind": "local",
            "device_name": (config or {}).get("device_name", "本机"),
        }
    if kind == "bundle":
        errors = []
        for part in payload.get("parts", []):
            try:
                return read(db, part, start=start, end=end)
            except (OSError, ValueError, federation.HubUnavailable) as exc:
                errors.append(str(exc))
        raise ValueError("当次各端精确引用均已失效：" + "；".join(errors))
    if kind == "remote_reference":
        config = federation.hub_config(db)
        if not config:
            raise ValueError("未连接引用所属Hub")
        info = federation._hub_info(config)
        inner = references.routing_metadata(payload["hub_reference"])
        if (
            info["hub_id"] != payload.get("hub_id")
            or inner.get("kind") != "hub_document"
            or inner.get("hub_id") != info["hub_id"]
        ):
            raise ValueError("引用属于其他Hub或材料类型")
        result = federation._request(
            config,
            "/documents/read",
            {
                "hub_id": info["hub_id"],
                "document_epoch": inner["document_epoch"],
                "reference": payload["hub_reference"],
                **{k: v for k, v in [("start", start), ("end", end)] if v is not None},
            },
        )
        return {**result, "archive_scope": "hub"}
    raise ValueError("须使用文档搜索返回的精确引用")
