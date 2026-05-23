#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 FaicalOm_DZ

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import pathlib
import subprocess
import sys
from typing import Iterable


ROOT = pathlib.Path(__file__).resolve().parent
CHECKSUMS_FILE = ROOT / "checksums.sha256"
OPTIONAL_EXE = ROOT / "FitGirl_Repack_Ultra_Toolkit_v3_Original_Full.exe"
REQUIRED_FILES = [
    "FitGirl_Toolkit.bat",
    "_toolkit_ui.py",
    "Page_Link_Extractor.py",
    "Page_Link_Extractor_speed.py",
    "Direct_Link_Resolver.py",
    "Direct_Link_Resolver_Slow.py",
    "Download_Manager_Sender.py",
    "Download_Manager_Sender_Speed.py",
]
MIN_PYTHON = (3, 10)


def info(message: str) -> None:
    print(f"[INFO] {message}")


def ok(message: str) -> None:
    print(f"[OK]   {message}")


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def fail(message: str) -> None:
    print(f"[ERROR] {message}")


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_checksum_entries(lines: Iterable[str]) -> list[tuple[str, pathlib.Path]]:
    entries: list[tuple[str, pathlib.Path]] = []
    for raw_line in lines:
        line = raw_line.lstrip("\ufeff").strip()
        if not line or line.startswith("#"):
            continue
        try:
            digest, rel_path = line.split("  ", 1)
        except ValueError:
            raise ValueError(f"Invalid checksum line: {line}") from None
        entries.append((digest.strip().lower(), ROOT / rel_path.strip()))
    return entries


def runtime_check() -> int:
    failures: list[str] = []

    info(f"Workspace: {ROOT}")
    info(f"Python: {sys.version.split()[0]}")

    if sys.version_info < MIN_PYTHON:
        failures.append(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required, found {sys.version.split()[0]}"
        )
    else:
        ok(f"Python version is supported ({sys.version.split()[0]})")

    missing_files = [name for name in REQUIRED_FILES if not (ROOT / name).exists()]
    if missing_files:
        failures.append("Missing required files: " + ", ".join(missing_files))
    else:
        ok(f"All required files are present ({len(REQUIRED_FILES)})")

    dependency_versions: dict[str, str] = {}
    for package_name in ("requests", "playwright"):
        try:
            importlib.import_module(package_name)
            dependency_versions[package_name] = importlib.metadata.version(package_name)
            ok(f"Dependency available: {package_name} {dependency_versions[package_name]}")
        except Exception as exc:
            failures.append(f"Dependency check failed for {package_name}: {exc}")

    if "playwright" in dependency_versions:
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_content("<html><body>runtime-check</body></html>")
                _ = page.text_content("body")
                browser.close()
            ok("Playwright Chromium runtime is available")
        except Exception as exc:
            failures.append(
                "Playwright is installed but Chromium launch failed. "
                f"Run 'python -m playwright install chromium'. Details: {exc}"
            )

    if OPTIONAL_EXE.exists():
        warn(
            "The bundled EXE is unsigned. Publish the SHA-256 hash and sign the file "
            "before calling it a trusted release."
        )

    if failures:
        for message in failures:
            fail(message)
        return 1

    ok("Runtime checks passed")
    return 0


def verify_checksums() -> int:
    if not CHECKSUMS_FILE.exists():
        fail("checksums.sha256 was not found.")
        return 1

    try:
        entries = iter_checksum_entries(CHECKSUMS_FILE.read_text(encoding="utf-8").splitlines())
    except ValueError as exc:
        fail(str(exc))
        return 1

    mismatches: list[str] = []
    for expected_digest, path in entries:
        relative_path = path.relative_to(ROOT)
        if not path.exists():
            mismatches.append(f"Missing file: {relative_path}")
            continue
        actual_digest = file_sha256(path)
        if actual_digest.lower() != expected_digest:
            mismatches.append(f"Hash mismatch: {relative_path}")
        else:
            ok(f"Hash verified: {relative_path}")

    if mismatches:
        for message in mismatches:
            fail(message)
        return 1

    ok("All checksums match")
    return 0


def exe_audit() -> int:
    if not OPTIONAL_EXE.exists():
        fail(f"{OPTIONAL_EXE.name} was not found.")
        return 1

    info(f"File: {OPTIONAL_EXE.name}")
    info(f"Size: {OPTIONAL_EXE.stat().st_size} bytes")
    info(f"SHA-256: {file_sha256(OPTIONAL_EXE)}")

    powershell = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "$sig = Get-AuthenticodeSignature -FilePath "
            f"'{OPTIONAL_EXE}'; "
            "Write-Output ('SignatureStatus=' + $sig.Status); "
            "Write-Output ('SignatureType=' + $sig.SignatureType)"
        ),
    ]
    try:
        result = subprocess.run(
            powershell,
            capture_output=True,
            text=True,
            check=False,
            cwd=str(ROOT),
        )
        output = (result.stdout or result.stderr).strip()
        if output:
            print(output)
    except Exception as exc:
        warn(f"Authenticode status check failed: {exc}")

    warn(
        "This EXE is a PyInstaller one-file bundle with no publisher metadata. "
        "Treat it as an opaque binary unless you can publish its source or a signed build."
    )
    return 0


def main() -> int:
    command = sys.argv[1].strip().lower() if len(sys.argv) > 1 else "runtime-check"

    if command == "runtime-check":
        return runtime_check()
    if command == "verify-checksums":
        return verify_checksums()
    if command == "exe-audit":
        return exe_audit()

    fail("Unknown command. Use: runtime-check | verify-checksums | exe-audit")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
