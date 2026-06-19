# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 FaicalOm_DZ
#
# FitGirl Repack Ultra Toolkit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License v3.0 or later.

import asyncio
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

# ================== SETTINGS ==================
HEADLESS = True
CONCURRENCY = 8
CONCURRENCY_SAFE = 4
DEBUG_LOGS = False
DEBUG_SCREENSHOTS = False

MAX_RETRIES = 2
PAGE_TIMEOUT = 9000
SAFE_PAGE_TIMEOUT = 15000
JS_SETTLE_DELAY = 0.65

LINKS_FILE = "fuckingfast_links.txt"
LOG_FILE   = "failed_links.txt"

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://fuckingfast.co/",
    "Upgrade-Insecure-Requests": "1",
}


def detect_system_browser_channel() -> Optional[str]:
    channel_paths = [
        ("msedge", [
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        ]),
        ("chrome", [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        ]),
    ]
    for channel, paths in channel_paths:
        if any(path.exists() for path in paths if str(path)):
            return channel
    return None


async def launch_compatible_browser(playwright):
    executable_path = Path(playwright.chromium.executable_path)
    if executable_path.exists():
        try:
            return await playwright.chromium.launch(
                executable_path=str(executable_path),
                headless=HEADLESS,
            )
        except Exception as exc:
            log(f"[WARN] Playwright full Chromium failed ({type(exc).__name__})")

    try:
        return await playwright.chromium.launch(headless=HEADLESS)
    except Exception as exc:
        channel = detect_system_browser_channel()
        if not channel:
            raise
        log(f"[WARN] Playwright Chromium failed ({type(exc).__name__}); using installed {channel}")
        return await playwright.chromium.launch(channel=channel, headless=HEADLESS)

# ================== REGEX PATTERNS ==================
_FF_DL = r"https?://(?:dl\.)?fuckingfast\.co/dl/"

REGEX_PATTERNS = [
    re.compile(
        r'window\.open\s*\(\s*["\'\`]\s*(' + _FF_DL + r'[^"\'\`]{10,})["\'\`]',
        re.IGNORECASE,
    ),
    re.compile(_FF_DL + r'[a-zA-Z0-9_\-\.%]+[^"\'\s<>)\\]+'),
    re.compile(r'"(' + _FF_DL + r'[^"]+)"'),
    re.compile(r"'(" + _FF_DL + r"[^']+)'"),
]

_URL_JUNK_TAIL = re.compile(r'[)\]\'">\\\,\s]+$')


def _sanitize_url(raw: str) -> str:
    return _URL_JUNK_TAIL.sub("", raw.strip())


def extract_filename_from_url(url: str, index: int) -> str:
    if "#" in url:
        name = url.split("#", 1)[1].strip()
        if name:
            return unquote(name)
    return f"file_{index:03d}"


resolved_map: dict[int, tuple] = {}   # index -> (filename, real_url)
file_lock = asyncio.Lock()
failed_first_pass: list[tuple] = []
final_failed:      list[tuple] = []


def log(message: str) -> None:
    if DEBUG_LOGS or any(m in message for m in ["OK", "FAILED", "Retry", "[INFO]", "[WARN]", "[ERROR]", "[SUMMARY]"]):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        print(line)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


async def block_resources(route) -> None:
    if route.request.resource_type in {"image", "font", "stylesheet", "media"}:
        await route.abort()
    else:
        await route.continue_()


def extract_direct_link_from_source(html: str) -> Optional[str]:
    for pattern in REGEX_PATTERNS:
        m = pattern.search(html)
        if m:
            raw = m.group(1) if m.lastindex else m.group(0)
            candidate = _sanitize_url(raw)
            if "fuckingfast.co/dl/" in candidate and len(candidate) > 40:
                return candidate
    return None


async def flush_resolved(links: list) -> None:
    """Rewrite resolved_manifest.txt with all resolved entries so far."""
    async with file_lock:
        with open("resolved_manifest.txt", "w", encoding="utf-8") as fh:
            for idx in range(1, len(links) + 1):
                if idx in resolved_map:
                    fn, real_url = resolved_map[idx]
                    fh.write(f"{idx}|{fn}|{real_url}\n")


async def process_single_link(
    context,
    link: str,
    index: int,
    filename: str,
    total: int,
    links: list,
    semaphore: asyncio.Semaphore,
    safe_mode: bool = False,
    fail_list: Optional[list] = None,
) -> bool:
    async with semaphore:
        log(f"[{index}/{total}] Processing...")

        for attempt in range(1, MAX_RETRIES + 1):
            is_safe = safe_mode or (attempt == 2)

            captured_for_current: list[str] = []
            request_event = asyncio.Event()

            def capture_direct_link(request) -> None:
                url = request.url
                if "dl.fuckingfast.co/dl/" in url and url not in captured_for_current:
                    captured_for_current.append(url)
                    request_event.set()

            page = None
            try:
                page = await context.new_page()
                await page.route("**/*", block_resources)
                page.on("request", capture_direct_link)

                await page.goto(
                    link,
                    wait_until="domcontentloaded",
                    timeout=SAFE_PAGE_TIMEOUT if is_safe else PAGE_TIMEOUT,
                )

                await asyncio.sleep(JS_SETTLE_DELAY)

                html_source = await page.content()
                real_url = extract_direct_link_from_source(html_source)

                if not real_url:
                    try:
                        js_urls: list = await page.evaluate(
                            """() => Array.from(document.querySelectorAll('a[href]'))
                                    .map(a => a.href)
                                    .filter(h => h.includes('fuckingfast.co/dl/'))"""
                        )
                        if js_urls:
                            candidate = _sanitize_url(js_urls[0])
                            if "fuckingfast.co/dl/" in candidate and len(candidate) > 40:
                                real_url = candidate
                    except Exception:
                        pass

                if not real_url and captured_for_current:
                    real_url = captured_for_current[0]

                if not real_url:
                    try:
                        await asyncio.wait_for(request_event.wait(), timeout=3.0)
                        real_url = captured_for_current[0] if captured_for_current else None
                    except asyncio.TimeoutError:
                        pass

                if real_url:
                    async with file_lock:
                        resolved_map[index] = (filename, real_url)
                    await flush_resolved(links)
                    log(f"[{index}/{total}] OK")
                    await page.close()
                    return True

                log(f"[{index}/{total}] [WARN] Attempt {attempt} failed — no direct link found")
                await page.close()

            except Exception as exc:
                if page:
                    await page.close()
                if attempt == MAX_RETRIES:
                    if fail_list is not None:
                        fail_list.append((index, link, filename))
                    log(f"[{index}/{total}] FAILED ({type(exc).__name__})")
                    return False
                await asyncio.sleep(1)

        if fail_list is not None:
            fail_list.append((index, link, filename))
        log(f"[{index}/{total}] FAILED")
        return False


async def main() -> None:
    start_time = time.perf_counter()
    log(f"[INFO] Direct Link Resolver — Concurrency: {CONCURRENCY} | Safe: {CONCURRENCY_SAFE}")

    open("resolved_manifest.txt", "w", encoding="utf-8").close()

    if not os.path.exists(LINKS_FILE):
        log(f"[ERROR] {LINKS_FILE} not found. Run Page_Link_Extractor_speed.py first.")
        return

    with open(LINKS_FILE, "r", encoding="utf-8") as fh:
        links = [line.strip() for line in fh if line.strip()]

    if not links:
        log("[ERROR] fuckingfast_links.txt is empty.")
        return

    log(f"[INFO] Loaded {len(links)} link(s)")

    async with async_playwright() as playwright:
        browser = await launch_compatible_browser(playwright)
        context = await browser.new_context(
            accept_downloads=False,
            user_agent=BROWSER_USER_AGENT,
            extra_http_headers=BROWSER_HEADERS,
            locale="en-US",
            viewport={"width": 1366, "height": 768},
        )
        await context.route("**/*", block_resources)

        semaphore = asyncio.Semaphore(CONCURRENCY)
        tasks = [
            process_single_link(
                context,
                link,
                idx,
                extract_filename_from_url(link, idx),
                len(links),
                links,
                semaphore,
                fail_list=failed_first_pass,
            )
            for idx, link in enumerate(links, 1)
        ]
        await asyncio.gather(*tasks)

        if failed_first_pass:
            log(f"[INFO] Safe retry for {len(failed_first_pass)} failed link(s)...")
            safe_semaphore = asyncio.Semaphore(CONCURRENCY_SAFE)
            retry_tasks = [
                process_single_link(
                    context,
                    link,
                    idx,
                    filename,
                    len(links),
                    links,
                    safe_semaphore,
                    safe_mode=True,
                    fail_list=final_failed,
                )
                for idx, link, filename in failed_first_pass
            ]
            await asyncio.gather(*retry_tasks)

        if final_failed:
            log(f"[WARN] {len(final_failed)} link(s) failed permanently — logged in failed_links.txt")
            with open(LOG_FILE, "a", encoding="utf-8") as fh:
                for idx, link, fn in final_failed:
                    fh.write(f"  PERM_FAIL | {idx} | {fn} | {link}\n")
        else:
            log("[OK] No links failed permanently")

        elapsed = time.perf_counter() - start_time
        total   = len(links)
        success = len(resolved_map)
        failed  = len(final_failed)
        rate    = (success / total * 100) if total else 0.0

        log("[SUMMARY] Final report:")
        log(f"   Total    : {total}")
        log(f"   Resolved : {success}")
        log(f"   Failed   : {failed}")
        log(f"   Rate     : {rate:.1f}%")
        log(f"   Time     : {elapsed:.1f}s")
        log("[OK] Stage 2 finished — resolved_manifest.txt is ready.")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
