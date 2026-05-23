# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 FaicalOm_DZ
#
# FitGirl Repack Ultra Toolkit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License v3.0 or later.

import os
import re
import subprocess
import sys
import time
import winreg
from collections import defaultdict
from datetime import datetime
from urllib.parse import unquote

# ── Enable ANSI on Windows ────────────────────────────────────────────────────
os.system("")
try:
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(
        ctypes.windll.kernel32.GetStdHandle(-11), 7
    )
except Exception:
    pass

R  = "\033[91m"
G  = "\033[92m"
Y  = "\033[93m"
C  = "\033[96m"
W  = "\033[97m"
B  = "\033[1m"
D  = "\033[2m"
RS = "\033[0m"

LOG_FILE          = "failed_links.txt"
LINKS_FILE        = "fuckingfast_links.txt"
MANIFEST_FILE     = "resolved_manifest.txt"
RESOLVER_FAST     = "Direct_Link_Resolver.py"
RESOLVER_SLOW     = "Direct_Link_Resolver_Slow.py"


# ─────────────────────────────────────────────────────────────────────────────
#  Logging
# ─────────────────────────────────────────────────────────────────────────────

def log(message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  IDM detection
# ─────────────────────────────────────────────────────────────────────────────

def find_idm_path():
    possible_paths = [
        r"C:\Program Files (x86)\Internet Download Manager\IDMan.exe",
        r"C:\Program Files\Internet Download Manager\IDMan.exe",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path

    registry_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Internet Download Manager"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Internet Download Manager"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Internet Download Manager"),
    ]
    for root, reg_path in registry_paths:
        try:
            with winreg.OpenKey(root, reg_path) as key:
                install_location, _ = winreg.QueryValueEx(key, "InstallLocation")
                idm_exe = os.path.join(install_location, "IDMan.exe")
                if os.path.exists(idm_exe):
                    return idm_exe
        except Exception:
            pass

    log("[ERROR] IDM not found automatically.")
    custom_path = input("Paste the full path to IDMan.exe: ").strip().strip('"')
    if custom_path and os.path.exists(custom_path):
        return custom_path
    return None


IDM_PATH = find_idm_path()
if not IDM_PATH:
    log("[ERROR] IDM was not found.")
    input("Press Enter to exit...")
    raise SystemExit(1)


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def extract_filename_from_url(url: str, index: int) -> str:
    if "#" in url:
        name = url.split("#", 1)[1].strip()
        if name:
            return unquote(name)
    return f"file_{index:03d}"


def idm_safe_filename(name: str, fallback: str = "download.bin") -> str:
    cleaned = os.path.basename((name or "").strip())
    if not cleaned:
        cleaned = fallback
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", cleaned)
    cleaned = cleaned.rstrip(" .")
    return cleaned or fallback


def get_base_name(filename: str) -> str:
    name = re.sub(r'\.part\d+\.\w+$', '', filename, flags=re.I)
    if name != filename:
        return name.strip()
    name = re.sub(r'\.\w+$', '', filename)
    return name.strip() if name else filename


def get_addon_group_name(filename: str) -> str:
    lower = filename.lower()
    if "setup" in lower or lower.endswith(".exe"):
        return filename
    base = get_base_name(filename)
    return base if base else "other-addons"


def get_part_number(filename: str) -> int:
    match = re.search(r"part0*(\d+)\.rar", filename, re.I)
    return int(match.group(1)) if match else 999999


def classify(filename: str) -> str:
    lower = filename.lower()
    if re.search(r"part\d+\.rar", lower) and not any(
        t in lower for t in ["optional", "selective", "bonus", "soundtrack",
                              "fg-optional", "language", "voice", "dlc",
                              "setup", ".exe", "bin"]
    ):
        return "MAIN_PART"
    return "ADDON"


# ─────────────────────────────────────────────────────────────────────────────
#  Read fuckingfast_links.txt → build file list
# ─────────────────────────────────────────────────────────────────────────────

if not os.path.exists(LINKS_FILE):
    log(f"[ERROR] {LINKS_FILE} not found.")
    input("Press Enter to exit...")
    raise SystemExit(1)

log(f"[OK] Reading {LINKS_FILE}...")

files = []
with open(LINKS_FILE, "r", encoding="utf-8") as fh:
    for idx, line in enumerate(fh, 1):
        line = line.strip()
        if not line:
            continue
        filename = extract_filename_from_url(line, idx)
        files.append({"index": idx, "filename": filename, "source_url": line})

for item in files:
    item["category"] = classify(item["filename"])

main_parts  = sorted([f for f in files if f["category"] == "MAIN_PART"],
                     key=lambda x: get_part_number(x["filename"]))
addon_files = [f for f in files if f["category"] == "ADDON"]

addon_groups: defaultdict = defaultdict(list)
for item in addon_files:
    addon_groups[get_addon_group_name(item["filename"])].append(item)

log(f"[OK] Loaded {len(files)} files")
log(f"   MAIN PARTS  : {len(main_parts)}")
log(f"   ADDON GROUPS: {len(addon_groups)}")


# ─────────────────────────────────────────────────────────────────────────────
#  IDM send helpers
# ─────────────────────────────────────────────────────────────────────────────

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def send_one_to_idm_queue(real_url: str, filename: str, index: int) -> None:
    try:
        proc = subprocess.Popen(
            [IDM_PATH, "/n", "/d", real_url, "/f",
             idm_safe_filename(filename, f"file_{index:03d}.bin"), "/a"],
            shell=False,
            creationflags=_NO_WINDOW,
        )
        proc.wait()   # wait for IDM registration to finish, but no visible window
    except Exception as exc:
        log(f"   [ERROR] IDM queue add failed [{index}] {filename}: {exc}")


def send_one_to_idm_start(real_url: str, filename: str, index: int,
                          start_delay: float) -> None:
    try:
        proc = subprocess.Popen(
            [IDM_PATH, "/n", "/d", real_url, "/f",
             idm_safe_filename(filename, f"file_{index:03d}.bin")],
            shell=False,
            creationflags=_NO_WINDOW,
        )
        proc.wait()
        log(f"   [{index}] Sent: {filename}")
        time.sleep(start_delay)
    except Exception as exc:
        log(f"   [ERROR] IDM start failed [{index}] {filename}: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
#  Read resolved_manifest.txt → dict { index: (filename, real_url) }
# ─────────────────────────────────────────────────────────────────────────────

def read_manifest() -> dict:
    result = {}
    if not os.path.exists(MANIFEST_FILE):
        return result
    try:
        with open(MANIFEST_FILE, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or "|" not in line:
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) < 3:
                    continue
                try:
                    idx      = int(parts[0])
                    filename = parts[1]
                    real_url = parts[2]
                    result[idx] = (filename, real_url)
                except Exception:
                    continue
    except Exception:
        pass
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  Red progress bar
# ─────────────────────────────────────────────────────────────────────────────

def show_resolve_progress(resolver_proc, total: int, selected_indices: set) -> None:
    """
    Show a red progress bar while resolver_proc is running.
    Counts lines in resolved_manifest.txt as they arrive.
    Waits until resolver finishes.
    """
    width = 52
    print()
    print(f"  {B}Resolving direct links — {C}{total}{RS}{B} file(s){RS}\n")

    while True:
        done = 0
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as fh:
                done = sum(1 for ln in fh if ln.strip())
        except Exception:
            pass

        pct    = min(done / total, 1.0) if total else 1.0
        filled = int(width * pct)
        bar    = R + "█" * filled + D + "░" * (width - filled) + RS
        sys.stdout.write(f"\r  [{bar}]  {B}{done:>3}/{total}{RS}  {pct*100:5.1f}%")
        sys.stdout.flush()

        if resolver_proc.poll() is not None and done >= total:
            break
        if resolver_proc.poll() is not None:
            time.sleep(0.5)
            try:
                with open(MANIFEST_FILE, "r", encoding="utf-8") as fh:
                    done = sum(1 for ln in fh if ln.strip())
            except Exception:
                pass
            pct    = min(done / total, 1.0) if total else 1.0
            filled = int(width * pct)
            bar    = R + "█" * filled + D + "░" * (width - filled) + RS
            sys.stdout.write(f"\r  [{bar}]  {B}{done:>3}/{total}{RS}  {pct*100:5.1f}%")
            sys.stdout.flush()
            break

        time.sleep(0.8)

    print(f"\n\n  {G}✓  Resolver finished{RS}\n")


# ─────────────────────────────────────────────────────────────────────────────
#  "Start immediately" mode — stream links from manifest as resolver works
# ─────────────────────────────────────────────────────────────────────────────

def stream_send_immediate(resolver_proc, selected_indices: set,
                          start_delay: float, total: int) -> None:
    """
    Launch Direct_Link_Resolver_Slow in background, then poll resolved_manifest.txt.
    Send each resolved link that is in selected_indices to IDM immediately,
    without waiting for the resolver to complete.
    """
    sent       = set()
    sent_count = 0
    need_count = len(selected_indices)

    log(f"[INFO] Streaming {need_count} selected file(s) to IDM as links resolve...")

    while True:
        manifest = read_manifest()
        for idx, (fn, real_url) in manifest.items():
            if idx in selected_indices and idx not in sent:
                send_one_to_idm_start(real_url, fn, idx, start_delay)
                sent.add(idx)
                sent_count += 1

        # Done if resolver exited AND all selected links sent
        if resolver_proc.poll() is not None and sent_count >= need_count:
            break

        # Done if all selected links already resolved (resolver may still run for others)
        if sent_count >= need_count:
            break

        time.sleep(2.0)

    log(f"[OK] Sent {sent_count}/{need_count} selected files to IDM (immediate).")


# ─────────────────────────────────────────────────────────────────────────────
#  "Queue only" mode — wait for resolver, then bulk-add
# ─────────────────────────────────────────────────────────────────────────────

def bulk_send_queue(selected_indices: set) -> None:
    manifest = read_manifest()
    to_send  = [(idx, fn, url) for idx, (fn, url) in sorted(manifest.items())
                if idx in selected_indices]

    if not to_send:
        log("[WARN] No resolved links found for selected files.")
        return

    count       = len(to_send)
    smart_delay = max(0.1, min(0.45, 5.0 / count)) if count > 0 else 0.45
    log(f"[INFO] Adding {count} links to IDM queue (delay: {smart_delay:.2f}s/file)...")

    for idx, fn, real_url in to_send:
        send_one_to_idm_queue(real_url, fn, idx)
        time.sleep(smart_delay)

    log(f"[OK] {count} file(s) added to IDM queue.")


# ─────────────────────────────────────────────────────────────────────────────
#  UI helpers
# ─────────────────────────────────────────────────────────────────────────────

def show_preview(selected: list) -> None:
    print(f"\n  Selected files ({B}{len(selected)}{RS}):")
    for i, item in enumerate(selected[:10], 1):
        print(f"   {D}[{i}]{RS} {item['filename']}")
    if len(selected) > 10:
        print(f"   {D}... and {len(selected) - 10} more{RS}")


def sep(char: str = "─", width: int = 70) -> str:
    return "  " + char * width


# ─────────────────────────────────────────────────────────────────────────────
#  Main loop
# ─────────────────────────────────────────────────────────────────────────────

while True:
    print()
    print(sep("═"))
    print(f"  {B}{Y}FitGirl Repack Ultra Toolkit — Download Manager{RS}")
    print(sep("═"))
    print(f"  {W}1{RS} - Send ALL files  {D}({len(files)} total){RS}")
    print(f"  {W}2{RS} - MAIN game parts only  {D}({len(main_parts)} parts){RS}")
    print(f"  {W}3{RS} - ADDONS / optional / bonus  {D}({len(addon_groups)} groups){RS}")
    print(f"  {W}0{RS} - Cancel and exit")
    print(sep("─"))

    choice = input(f"\n  {B}Enter choice (0-3):{RS} ").strip()

    if choice == "0":
        log("[INFO] Cancelled by user.")
        break

    selected = []

    if choice == "1":
        selected = files[:]

    elif choice == "2":
        print(f"\n  {B}MAIN GAME PARTS{RS}  ({len(main_parts)} parts)")
        print(f"  {W}1{RS} - All main parts")
        print(f"  {W}2{RS} - Range  (e.g. 10/20)")
        print(f"  {W}3{RS} - Specific  (e.g. 1/5/10)")
        print(f"  {W}0{RS} - Back")
        sub = input("  Choice: ").strip()

        if sub == "1":
            selected = main_parts[:]
        elif sub == "2":
            rng = input("  From / To (e.g. 10/20): ").strip()
            try:
                first, last = map(int, re.split(r"[,/;\s]+", rng)[:2])
                first, last = min(first, last), max(first, last)
                selected = [main_parts[i - 1] for i in range(first, last + 1)
                            if 1 <= i <= len(main_parts)]
            except Exception:
                log("[ERROR] Invalid range.")
                continue
        elif sub == "3":
            nums = input("  Parts (e.g. 1/5/10): ").strip()
            nums_list = [int(v) for v in re.split(r"[,/;\s]+", nums) if v.isdigit()]
            selected = [main_parts[n - 1] for n in nums_list if 1 <= n <= len(main_parts)]
        else:
            continue

    elif choice == "3":
        print(f"\n  {B}ADDONS / OPTIONAL GROUPS{RS}")
        print(sep("─"))
        groups_list = list(addon_groups.items())
        for i, (gname, gfiles) in enumerate(groups_list, 1):
            print(f"  {W}{i}{RS} - {gname}  {D}({len(gfiles)} files){RS}")
        print(f"  {W}0{RS} - Back")
        print(sep("─"))

        gc = input("\n  Choose group: ").strip()
        if gc == "0":
            continue
        try:
            gi = int(gc) - 1
            gname, gfiles = groups_list[gi]
        except Exception:
            log("[ERROR] Invalid group selection.")
            continue

        print(f"\n  {B}{gname}{RS}")
        for i, item in enumerate(gfiles, 1):
            print(f"   {i} - {item['filename']}")

        print(f"\n  {W}1{RS} - All files in this group")
        print(f"  {W}2{RS} - Specific files")
        print(f"  {W}0{RS} - Back")
        sub = input("  Choice: ").strip()

        if sub == "1":
            selected = gfiles[:]
        elif sub == "2":
            nums = input("  Numbers (e.g. 1/3/5): ").strip()
            nums_list = [int(v) for v in re.split(r"[,/;\s]+", nums) if v.isdigit()]
            selected = [gfiles[n - 1] for n in nums_list if 1 <= n <= len(gfiles)]
        else:
            continue
    else:
        log("[ERROR] Invalid choice.")
        continue

    if not selected:
        log("[ERROR] No files selected.")
        continue

    show_preview(selected)
    confirm = input(f"\n  {B}Confirm? (Y/N):{RS} ").strip().upper()
    if confirm != "Y":
        log("[INFO] Cancelled by user.")
        continue

    selected_indices = {item["index"] for item in selected}
    total_links      = len(files)

    # ── IDM action choice ──────────────────────────────────────────────────
    print()
    print(sep("─"))
    print(f"  {B}IDM ACTION{RS}")
    print(sep("─"))
    print(f"  {W}1{RS} - {B}Start downloading immediately{RS}")
    print(f"      Launches resolver in background, sends links to IDM as they arrive")
    print(f"  {W}2{RS} - {B}Add to IDM queue only{RS}")
    print(f"      Waits for full resolve, then adds all to IDM queue")
    print(f"  {W}0{RS} - Back")
    print(sep("─"))
    action = input(f"\n  {B}Choice:{RS} ").strip()

    if action == "0":
        continue

    # ── Option 1: Immediate download ──────────────────────────────────────
    if action == "1":
        delay_input = input(f"  Delay between sending files to IDM (seconds) [{D}default 2{RS}]: ").strip()
        try:
            start_delay = float(delay_input) if delay_input else 2.0
        except ValueError:
            start_delay = 2.0

        log("[INFO] Launching Direct_Link_Resolver_Slow.py in background...")
        # Clear manifest before starting
        open(MANIFEST_FILE, "w", encoding="utf-8").close()

        resolver_proc = subprocess.Popen(
            [sys.executable, RESOLVER_SLOW],
            creationflags=_NO_WINDOW,
        )
        log(f"[OK] Resolver started (PID {resolver_proc.pid}). Streaming links to IDM...")

        stream_send_immediate(resolver_proc, selected_indices, start_delay, total_links)

    # ── Option 2: Queue only ───────────────────────────────────────────────
    elif action == "2":
        log("[INFO] Launching Direct_Link_Resolver.py (full resolve before queue)...")
        open(MANIFEST_FILE, "w", encoding="utf-8").close()

        resolver_proc = subprocess.Popen(
            [sys.executable, RESOLVER_FAST],
            creationflags=_NO_WINDOW,
        )
        log(f"[OK] Resolver started (PID {resolver_proc.pid}). Progress:")

        show_resolve_progress(resolver_proc, total_links, selected_indices)

        log("[INFO] Adding selected files to IDM queue...")
        bulk_send_queue(selected_indices)

    else:
        log("[ERROR] Invalid action.")
        continue

    log("[OK] Operation completed successfully.")

    clean = input(f"\n  {B}Clean fuckingfast_links.txt + resolved_manifest.txt? (Y/N):{RS} ").strip().upper()
    if clean == "Y":
        for f in (LINKS_FILE, MANIFEST_FILE):
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass
        log("[OK] Temp files removed.")

    break

input(f"\n  {D}Press Enter to exit...{RS}")
