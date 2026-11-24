"""Observe the 007 Hub credential boundary in an actual isolated browser.

Complements TC-007-user-discovery; never connects to daily archives.
"""

from __future__ import annotations
import argparse
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import traceback
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hub_documents_platform import Probe, now, sha


def private_snapshot(snapshot, token):
    assert token not in json.dumps(snapshot, ensure_ascii=False)


async def observe(probe):
    from playwright.async_api import async_playwright, expect

    probe.prepare()
    pub = subprocess.run(
        ["openssl", "x509", "-in", str(probe.ca), "-pubkey", "-noout"],
        capture_output=True,
        check=True,
    ).stdout
    der = subprocess.run(
        ["openssl", "pkey", "-pubin", "-outform", "der"],
        input=pub,
        capture_output=True,
        check=True,
    ).stdout
    pin = base64.b64encode(hashlib.sha256(der).digest()).decode()
    probe.save(
        "privacy-tls",
        {
            "trust": "only generated task certificate SPKI",
            "pin": pin,
            "certificate_sha256": sha(probe.ca.read_bytes()),
        },
    )
    good = {
        "url": "https://example.invalid/",
        "local": [],
        "session": [],
        "cookies": [],
    }
    private_snapshot(good, probe.token)
    for field in good:
        try:
            private_snapshot({**good, field: probe.token}, probe.token)
        except AssertionError:
            pass
        else:
            raise AssertionError("storage detector did not reject " + field)
    probe.save(
        "privacy-selfcheck",
        {"url_local_session_cookie_negative_samples_rejected": True},
    )
    async with async_playwright() as engine:
        browser = await engine.chromium.launch(
            headless=True,
            args=["--ignore-certificate-errors-spki-list=" + pin],
            **(
                {"executable_path": probe.config["browser"]}
                if probe.config.get("browser")
                else {}
            ),
        )
        context = await browser.new_context(viewport={"width": 1280, "height": 1000})
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = await context.new_page()
        network = []
        errors = []
        stages = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def seen(request):
            authorization = request.headers.get("authorization")
            origin = urlsplit(request.url)
            expected = urlsplit(probe.address["hub"])
            network.append(
                {
                    "url": request.url,
                    "method": request.method,
                    "has_authorization": bool(authorization),
                    "authorization_matches_task": authorization
                    == "Bearer " + probe.token,
                    "same_origin": (origin.scheme, origin.netloc)
                    == (expected.scheme, expected.netloc),
                }
            )

        page.on("request", seen)

        async def snapshot(stage):
            value = await page.evaluate(
                "({url:location.href,local:Object.entries(localStorage),session:Object.entries(sessionStorage)})"
            )
            value["cookies"] = await context.cookies()
            private_snapshot(value, probe.token)
            assert not any(probe.token in entry["url"] for entry in network)
            assert all(
                entry["same_origin"] and entry["authorization_matches_task"]
                for entry in network
                if entry["has_authorization"]
            )
            stages.append(
                {
                    "stage": stage,
                    "browser_state": value,
                    "no_token_in_url_or_stores": True,
                }
            )
            await page.screenshot(
                path=str(probe.out / ("privacy-" + stage + ".png")), full_page=True
            )

        try:
            await page.goto(probe.address["hub"])
            await expect(page.locator("#credential")).to_be_visible()
            await expect(page.locator("#workspace")).to_be_hidden()
            assert not any("/v1/" in entry["url"] for entry in network)
            await snapshot("anonymous")
            await page.locator("#credential").set_input_files(str(probe.token_file))
            await expect(page.locator("#workspace")).to_be_visible()
            assert any(entry["has_authorization"] for entry in network)
            assert await page.locator("#credential").input_value() == ""
            await snapshot("authenticated")
            marker = len(network)
            await page.reload()
            await expect(page.locator("#workspace")).to_be_hidden()
            await expect(page.locator("#credential")).to_be_visible()
            await page.wait_for_load_state("networkidle")
            assert not any(
                "/v1/" in entry["url"] or entry["has_authorization"]
                for entry in network[marker:]
            )
            await snapshot("reloaded")
            await page.locator("#credential").set_input_files(str(probe.token_file))
            await expect(page.locator("#workspace")).to_be_visible()
            await page.locator("#hub-scope").select_option("all")
            await page.locator("#hub-limit").select_option("50")
            await page.locator("#hub-query").fill("e1needle")
            await page.locator("#hub-search-form").evaluate("(f)=>f.requestSubmit()")
            row = page.locator("#hub-results .result").filter(
                has=page.get_by_text("e1needle D native one", exact=True)
            )
            await expect(row).to_have_count(1)
            await row.get_by_role("button", name="读取原文", exact=True).click()
            await expect(page.locator("#hub-read-text")).to_have_text(
                "e1needle D native one"
            )
            await snapshot("reauthorized-read")
            assert not errors
            probe.save(
                "browser-privacy",
                {
                    "stages": stages,
                    "requests": network,
                    "page_errors": errors,
                    "reauthorized_exact_original": "e1needle D native one",
                    "no_persistent_credential": True,
                },
            )
            return {
                "status": "passed",
                "kind": "actual Hub browser credential storage/reload observation",
                "finished_at": now(),
            }
        finally:
            await context.tracing.stop(
                path=str(probe.out / "browser-privacy-trace.zip")
            )
            await context.close()
            await browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    probe = Probe(json.loads(args.target_config.read_text()), args.output.resolve())
    probe.save(
        "privacy-runner",
        {"path": str(Path(__file__)), "sha256": sha(Path(__file__).read_bytes())},
    )
    try:
        probe.save("result", asyncio.run(observe(probe)))
    except BaseException:
        probe.save("failure", {"traceback": traceback.format_exc()})
        raise
    finally:
        probe.cleanup()


if __name__ == "__main__":
    main()
