# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 FaicalOm_DZ
#
# FitGirl Repack Ultra Toolkit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License v3.0 or later.

import re
import time
from datetime import datetime
from urllib.parse import unquote

import requests

# ================== VERSION SETTINGS ==================
DEBUG_LOGS = False

# ================== REGEX PATTERNS ==================
_EXT = r'(?:part\d+\.(?:rar|zip|7z)|rar|zip|7z|setup\.exe|exe|bin|iso|dmg|pkg)'

_FF_PAGE_PATTERNS = [
    re.compile(
        r'https?://fuckingfast\.co/[a-zA-Z0-9]{6,}#[^\s"\'<>\)]*?\.' + _EXT,
        re.IGNORECASE,
    ),
    re.compile(
        r'"(https?://fuckingfast\.co/[^\s"\'<>\)]+?#[^\s"\'<>\)]+?\.' + _EXT + r')"',
        re.IGNORECASE,
    ),
    re.compile(
        r"'(https?://fuckingfast\.co/[^\s'<>]+?#[^\s'<>]+?\." + _EXT + r")'",
        re.IGNORECASE,
    ),
    re.compile(
        r'window\.open\s*\(\s*["\']?(https?://fuckingfast\.co/[^"\']+?#[^"\']+?\.' + _EXT + r')["\']?',
        re.IGNORECASE,
    ),
]

_JUNK_TAIL = re.compile(r'[)\]\'">\\ ,]+$')

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def log(message, log_file=None):
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {message}"
    if DEBUG_LOGS or any(m in message for m in ["[INFO]", "[OK]", "[WARN]", "[ERROR]"]):
        print(line)
    if log_file:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def extract_filename_from_url(url, index):
    if "#" in url:
        name = url.split("#", 1)[1].strip()
        if name:
            return unquote(name)
    return f"file_{index:03d}"


def extract_fuckingfast_links(html: str) -> list[str]:
    seen: dict[str, None] = {}
    for pattern in _FF_PAGE_PATTERNS:
        for m in pattern.finditer(html):
            raw = m.group(1) if m.lastindex else m.group(0)
            candidate = _JUNK_TAIL.sub("", raw.strip())
            if "fuckingfast.co" in candidate and "#" in candidate and len(candidate) > 30:
                seen.setdefault(candidate, None)
    log(f"[INFO] Found {len(seen)} valid game-file link(s)")
    return list(seen)


# ================== MAIN EXECUTION ==================
LOG_FILE = "failed_links.txt"

source_page_url = input("Paste source page URL: ").strip()

start_time = time.perf_counter()

log("[INFO] Fetching page with requests (no browser)...", LOG_FILE)
try:
    response = requests.get(source_page_url, headers=_HEADERS, timeout=10)
    response.raise_for_status()
except requests.RequestException as exc:
    log(f"[ERROR] Failed to fetch page: {exc}", LOG_FILE)
    raise SystemExit(1)

log(f"[OK] Page fetched: {source_page_url}", LOG_FILE)

html = response.text
unique_links = extract_fuckingfast_links(html)

elapsed = time.perf_counter() - start_time

if unique_links:
    # ── Only write fuckingfast_links.txt (single output file) ──
    with open("fuckingfast_links.txt", "w", encoding="utf-8") as fh:
        for link in unique_links:
            fh.write(link + "\n")

    log(f"[OK] Extracted {len(unique_links)} source links successfully", LOG_FILE)
    log(f"   First link : {unique_links[0]}", LOG_FILE)
    log(f"   Last link  : {unique_links[-1]}", LOG_FILE)
    log(f"   Total time : {elapsed:.3f} seconds", LOG_FILE)
    log("   Saved      : fuckingfast_links.txt", LOG_FILE)
else:
    log("[ERROR] No valid FuckingFast game-file links were found", LOG_FILE)
    log("   Check that Filehoster: FuckingFast exists on the page", LOG_FILE)
    log(f"   Total time : {elapsed:.3f} seconds", LOG_FILE)
    raise SystemExit(1)

log("[OK] Stage 1 finished. You can now proceed to Stage 2.", LOG_FILE)
