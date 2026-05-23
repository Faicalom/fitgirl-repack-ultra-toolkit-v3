# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 FaicalOm_DZ
#
# FitGirl Repack Ultra Toolkit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License v3.0 or later.

import re
import time
from datetime import datetime
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

# ================== VERSION SETTINGS ==================
HEADLESS = True
BLOCK_RESOURCES = True
DEBUG_LOGS = False

PAGE_TIMEOUT = 20000
LOG_FILE     = "failed_links.txt"

# ================== REGEX PATTERNS ==================
_FF_PAGE_PATTERNS = [
    re.compile(r'https?://fuckingfast\.co/[a-zA-Z0-9]{6,}'),
    re.compile(r'https?://fuckingfast\.co/[^\s"\'<>\)]+'),
    re.compile(r'"(https?://fuckingfast\.co/[^"]+)"'),
    re.compile(r"'(https?://fuckingfast\.co/[^']+)'"),
    re.compile(r'window\.open\s*\(\s*["\']?(https?://fuckingfast\.co/[^"\']+)["\']?'),
]

_JUNK_TAIL = re.compile(r'[)\]\'">\\ ,]+$')

_GAME_EXT_RE = re.compile(
    r'\.(?:part\d+\.(?:rar|zip|7z)'
    r'|rar|zip|7z'
    r'|exe|bin|iso|dmg|pkg'
    r'|setup\.exe'
    r')$',
    re.IGNORECASE,
)


def log(message):
    if DEBUG_LOGS or any(m in message for m in ["[INFO]", "[OK]", "[WARN]", "[ERROR]"]):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        print(line)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def block_resources(route):
    if route.request.resource_type in ["image", "font", "stylesheet", "media"]:
        route.abort()
    else:
        route.continue_()


def extract_filename_from_url(url, index):
    if "#" in url:
        name = url.split("#", 1)[1].strip()
        if name:
            return unquote(name)
    return f"file_{index:03d}"


def _is_valid_game_file(url: str) -> bool:
    if "#" not in url:
        return False
    fragment = unquote(url.split("#", 1)[1].strip())
    return bool(_GAME_EXT_RE.search(fragment))


def extract_fuckingfast_links(html: str) -> list[str]:
    raw_seen:  dict[str, None] = {}
    good_seen: dict[str, None] = {}

    for pattern in _FF_PAGE_PATTERNS:
        for m in pattern.finditer(html):
            raw = m.group(1) if m.lastindex else m.group(0)
            candidate = _JUNK_TAIL.sub("", raw.strip())
            if "fuckingfast.co" in candidate and len(candidate) > 30:
                raw_seen.setdefault(candidate, None)

    log(f"[INFO] Raw candidates : {len(raw_seen)}")

    for url in raw_seen:
        if _is_valid_game_file(url):
            good_seen.setdefault(url, None)

    log(f"[INFO] After filter   : {len(good_seen)} (valid game-file links only)")
    return list(good_seen)


# ================== MAIN EXECUTION ==================
source_page_url = input("Paste source page URL: ").strip()

start_time = time.perf_counter()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=HEADLESS)
    context = browser.new_context()

    if BLOCK_RESOURCES:
        context.route("**/*", block_resources)

    page = context.new_page()

    log("[OK] Browser started in headless mode")
    page.goto(source_page_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
    log(f"[OK] Page opened: {source_page_url}")

    time.sleep(1.2)

    log("[INFO] Extracting FuckingFast links from page source...")
    html = page.content()
    unique_links = extract_fuckingfast_links(html)

    elapsed = time.perf_counter() - start_time

    if unique_links:
        # ── Only write fuckingfast_links.txt (single output file) ──
        with open("fuckingfast_links.txt", "w", encoding="utf-8") as fh:
            for link in unique_links:
                fh.write(link + "\n")

        log(f"[OK] Extracted {len(unique_links)} source links successfully", )
        log(f"   First link : {unique_links[0]}")
        log(f"   Last link  : {unique_links[-1]}")
        log(f"   Total time : {elapsed:.2f} seconds")
        log("   Saved      : fuckingfast_links.txt")
    else:
        log("[ERROR] No valid FuckingFast game-file links were found")
        log("   Check that Filehoster: FuckingFast exists on the page and links are visible")
        browser.close()
        raise SystemExit(1)

    browser.close()
    log("[OK] Stage 1 finished. You can now proceed to Stage 2.")
