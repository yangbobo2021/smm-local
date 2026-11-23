"""Opt-in 007 user-path and two real stale-page submissions on macOS.

Uses the independent installed-package probe fixtures. Never uses daily state.
"""

from __future__ import annotations
import argparse
import asyncio
import json
from pathlib import Path
import re
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hub_documents_platform import Probe, sha, now

ROOT = Path(__file__).resolve().parents[2]


async def observe(probe, second):
    from playwright.async_api import async_playwright, expect

    probe.prepare()
    # Follow actual repository links and invoke the installed CLI help, rather
    # than assuming a feature described only in the SPEC is discoverable.
    documents = {}
    for name in [
        "README.md",
        "TRIAL_GUIDE.md",
        "skills/smm-search/SKILL.md",
        "scripts/acceptance/README.md",
    ]:
        p = ROOT / name
        documents[name] = {"sha256": sha(p.read_bytes()), "text": p.read_text()}
    assert "TRIAL_GUIDE.md" in documents["README.md"]["text"]
    for needle in [
        "documents sync-status",
        "documents sync-policy",
        "hub-project-id",
        "默认",
        "暂停",
        "generation",
    ]:
        assert needle in documents["TRIAL_GUIDE.md"]["text"], needle
    for arguments in [
        ("documents", "--help"),
        ("documents", "sync-policy", "--help"),
        ("documents", "search", "--help"),
    ]:
        # Help exits before opening a database and emits human text, not JSON.
        probe.run(
            "user-help",
            probe.argv("a", "smm_local.cli", "--db", probe.db["a"], *arguments),
        )
    probe.save(
        "document-user-path",
        {
            "documents": documents,
            "followed": [
                "README.md",
                "TRIAL_GUIDE.md",
                "installed CLI help",
                "Local Web project/document controls",
                "skills/smm-search/SKILL.md",
                "scripts/acceptance/README.md",
            ],
            "scope": "repository discovery plus installed CLI and real Web; not a new agent conversation",
        },
    )
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            **(
                {"executable_path": probe.config["browser"]}
                if probe.config.get("browser")
                else {}
            ),
        )
        context = await browser.new_context(viewport={"width": 1280, "height": 1000})
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = await context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        async def row():
            return page.locator("#doc-sync-projects .result").filter(
                has=page.locator("p").filter(
                    has_text=re.compile(r"^A #" + str(probe.a["id"]) + r" ·")
                )
            )

        async def snapshot():
            status = probe.cli("a", "documents", "sync-status")
            project = next(
                p for p in status["projects"] if p["project_id"] == probe.a["id"]
            )
            return status, project

        async def submit_old(label, frozen, current):
            before = probe.cli("a", "documents", "sync-status")
            async with page.expect_response(
                lambda r: r.url.endswith("/documents/sync-policy")
                and r.request.method == "POST"
            ) as response:
                await (await row()).get_by_role(
                    "button", name="允许项目文档同步", exact=True
                ).click()
            reply = await response.value
            payload = reply.request.post_data_json
            body = await reply.json()
            assert reply.status == 400, (payload, body)
            assert payload == {
                "project_key": frozen["project_key"],
                "expected_hub_id": frozen["hub_id"],
                "expected_generation": frozen["generation"],
                "enabled": True,
            }
            after = probe.cli("a", "documents", "sync-status")
            assert after == before
            await expect(page.locator("#notice")).to_have_class(re.compile("error"))
            await page.screenshot(
                path=str(probe.out / (label + ".png")), full_page=True
            )
            probe.save(
                label,
                {
                    "frozen": frozen,
                    "current": current,
                    "request": payload,
                    "status": reply.status,
                    "response": body,
                    "before": before,
                    "after": after,
                    "visible_error": await page.locator("#notice").inner_text(),
                },
            )

        try:
            await page.goto(probe.address["a"])
            await page.locator("button[data-tab=documents]").click()
            await expect(await row()).to_be_visible()
            status, project = await snapshot()
            frozen = {
                "project_key": project["project_key"],
                "hub_id": status["hub_id"],
                "generation": project["generation"],
            }
            await expect(await row()).to_contain_text(
                "generation " + str(project["generation"])
            )
            await page.screenshot(
                path=str(probe.out / "same-hub-before.png"), full_page=True
            )
            probe.policy("a", probe.a, False)
            current, updated = await snapshot()
            assert updated["generation"] > frozen["generation"]
            await submit_old("same-hub-old-generation", frozen, current)
            await page.locator("#doc-sync-status").click()
            await expect(await row()).to_contain_text(
                "generation " + str(updated["generation"])
            )
            frozen = {
                "project_key": updated["project_key"],
                "hub_id": current["hub_id"],
                "generation": updated["generation"],
            }
            await page.screenshot(
                path=str(probe.out / "switch-hub-before.png"), full_page=True
            )
            # New independent Hub; reuse only this task's TLS certificate so
            # the client's configured trust remains identical across the switch.
            second.ca = probe.ca
            second.key = probe.key
            second.http = probe.http
            second.start("hub")
            result = probe.cli(
                "a",
                "configure-hub",
                second.address["hub"],
                "user-path-a",
                "--token-file",
                second.token_file,
            )
            assert result["connected"]
            probe.wait_idle("a")
            probe.policy("a", probe.a, True)
            probe.policy("a", probe.a, False)
            current, updated = await snapshot()
            assert (
                current["hub_id"] != frozen["hub_id"]
                and updated["generation"] == frozen["generation"]
            )
            await submit_old("different-hub-equal-generation", frozen, current)
            assert not errors
            probe.save("user-web-errors", {"errors": errors})
        finally:
            await context.tracing.stop(path=str(probe.out / "stale-pages-trace.zip"))
            await context.close()
            await browser.close()
    return {
        "status": "passed",
        "kind": "TC-007-user-discovery stale forms plus documented installed path",
        "finished_at": now(),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target-config", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    config = json.loads(args.target_config.read_text())
    assert sys.platform == "darwin"
    probe = Probe(config, args.output.resolve())
    second = Probe(config, args.output.resolve() / "second-context")
    probe.save(
        "user-path-runner",
        {"path": str(Path(__file__)), "sha256": sha(Path(__file__).read_bytes())},
    )
    try:
        result = asyncio.run(observe(probe, second))
        probe.save("result", result)
    except BaseException:
        probe.save("failure", {"traceback": traceback.format_exc()})
        raise
    finally:
        second.cleanup()
        probe.cleanup()
    print(json.dumps({"status": result["status"], "output": str(probe.out)}))


if __name__ == "__main__":
    main()
