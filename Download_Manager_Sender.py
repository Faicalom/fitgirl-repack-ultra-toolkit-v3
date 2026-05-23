# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 FaicalOm_DZ
#
# FitGirl Repack Ultra Toolkit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License v3.0 or later.

import os
import re
import subprocess
import time
import winreg
from collections import defaultdict
from datetime import datetime


LOG_FILE      = "failed_links.txt"
MANIFEST_FILE = "resolved_manifest.txt"


def log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


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

    print("[ERROR] IDM was not found automatically.")
    custom_path = input("Paste the full path to IDMan.exe: ").strip().strip('"')
    if custom_path and os.path.exists(custom_path):
        return custom_path
    return None


IDM_PATH = find_idm_path()
if not IDM_PATH:
    log("[ERROR] IDM was not found.")
    input("Press Enter to exit...")
    raise SystemExit(1)


IDM_DELAY = 0.45


def idm_safe_filename(name, fallback="download.bin"):
    cleaned = os.path.basename((name or "").strip())
    if not cleaned:
        cleaned = fallback
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", cleaned)
    cleaned = cleaned.rstrip(" .")
    return cleaned or fallback


def get_base_name(filename):
    name = re.sub(r'\.part\d+\.\w+$', '', filename, flags=re.I)
    if name != filename:
        return name.strip()
    name = re.sub(r'\.\w+$', '', filename)
    return name.strip() if name else filename


def get_addon_group_name(filename):
    lower = filename.lower()
    if "setup" in lower or lower.endswith(".exe"):
        return filename
    base = get_base_name(filename)
    return base if base else "other-addons"


def get_part_number(filename):
    match = re.search(r"part0*(\d+)\.rar", filename, re.I)
    return int(match.group(1)) if match else 999999


# ── Read resolved_manifest.txt  (format: idx|filename|real_url) ──────────────
if not os.path.exists(MANIFEST_FILE):
    log(f"[ERROR] {MANIFEST_FILE} was not found.")
    input("Press Enter to exit...")
    raise SystemExit(1)

log(f"[OK] Reading {MANIFEST_FILE}...")

files = []
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
            if not filename:
                filename = f"file_{idx:03d}"
            files.append({"index": idx, "filename": filename, "real_url": real_url})
        except Exception:
            continue


def classify(filename):
    lower = filename.lower()
    if re.search(r"part\d+\.rar", lower) and not any(
        t in lower for t in ["optional", "selective", "bonus", "soundtrack",
                              "fg-optional", "language", "voice", "dlc",
                              "setup", ".exe", "bin"]
    ):
        return "MAIN_PART"
    return "ADDON"


for item in files:
    item["category"] = classify(item["filename"])

main_parts  = sorted([f for f in files if f["category"] == "MAIN_PART"],
                     key=lambda x: get_part_number(x["filename"]))
addon_files = [f for f in files if f["category"] == "ADDON"]

addon_groups = defaultdict(list)
for item in addon_files:
    addon_groups[get_addon_group_name(item["filename"])].append(item)

log(f"[OK] Loaded {len(files)} files")
log(f"   MAIN PARTS  : {len(main_parts)}")
log(f"   ADDON GROUPS: {len(addon_groups)}")


_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def send_to_idm(files_to_send, mode="queue", start_delay=2.0):
    if mode == "queue":
        count = len(files_to_send)
        smart_delay = max(0.05, min(0.3, 3.0 / count)) if count > 0 else 0.3
        log(f"[INFO] Adding {count} links to the IDM queue...")
        log(f"[INFO] Smart delay: {smart_delay:.2f}s per file → ~{smart_delay * count:.1f}s total")
        for item in files_to_send:
            try:
                subprocess.Popen(
                    [IDM_PATH, "/n", "/d", item["real_url"], "/f",
                     idm_safe_filename(item["filename"], f"file_{item['index']:03d}.bin"), "/a"],
                    shell=False,
                    creationflags=_NO_WINDOW,
                )
                time.sleep(smart_delay)
            except Exception as exc:
                log(f"   [ERROR] Failed to add item: {str(exc)}")
        log("[OK] Added the selected files to the IDM queue.")
    else:
        log(f"[INFO] Starting immediate download for {len(files_to_send)} files (delay: {start_delay}s)...")
        for item in files_to_send:
            try:
                subprocess.Popen(
                    [IDM_PATH, "/n", "/d", item["real_url"], "/f",
                     idm_safe_filename(item["filename"], f"file_{item['index']:03d}.bin")],
                    shell=False,
                    creationflags=_NO_WINDOW,
                )
                print(f"   [{item['index']}] Successfully sent: {item['filename']}")
                time.sleep(start_delay)
            except Exception as exc:
                log(f"   [ERROR] Failed to send [{item['index']}] {item['filename']}: {str(exc)}")
        log("[OK] All files sent to IDM and downloading immediately.")


def clean_temp_files():
    # ── Only the 3 essential files are cleaned, nothing else ──
    temp_files = [
        "fuckingfast_links.txt",
        "resolved_manifest.txt",
        "failed_links.txt",
    ]
    for path in temp_files:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
    log("[OK] Temporary files cleaned.")


def show_preview(selected):
    print(f"\nSelected files ({len(selected)}):")
    for index, item in enumerate(selected[:10], 1):
        print(f"   [{index}] {item['filename']}")
    if len(selected) > 10:
        print(f"   ... and {len(selected) - 10} more")


while True:
    print("\n" + "=" * 75)
    print("          FitGirl Repack Ultra Toolkit - Download Manager Sender")
    print("=" * 75)
    print("1 - Send ALL files")
    print(f"2 - MAIN game parts only ({len(main_parts)})")
    print(f"3 - ADDONS / optional / bonus / setup / exe ({len(addon_groups)} groups)")
    print("0 - Cancel and exit")
    print("=" * 75)

    choice = input("\nEnter choice (0-3): ").strip()

    if choice == "0":
        log("[INFO] Operation cancelled by user.")
        break

    selected = []

    if choice == "1":
        selected = files
    elif choice == "2":
        print("\nMAIN GAME PARTS")
        print(f"Total main parts: {len(main_parts)}")
        print("1 - Send ALL main parts")
        print("2 - Send a RANGE of main parts")
        print("3 - Send SPECIFIC main parts")
        print("0 - Back")
        sub = input("Choice: ").strip()

        if sub == "1":
            selected = main_parts
        elif sub == "2":
            rng = input("From / To (example: 10/20 or 10 20): ").strip()
            try:
                first, last = map(int, re.split(r"[,/;\s]+", rng)[:2])
                first, last = min(first, last), max(first, last)
                selected = [main_parts[i - 1] for i in range(first, last + 1)
                            if 1 <= i <= len(main_parts)]
            except Exception:
                log("[ERROR] Invalid range.")
                continue
        elif sub == "3":
            nums = input("Specific parts (example: 1/5/10 or 1 5 10): ").strip()
            nums_list = [int(v) for v in re.split(r"[,/;\s]+", nums) if v.isdigit()]
            selected = [main_parts[n - 1] for n in nums_list if 1 <= n <= len(main_parts)]
        else:
            continue
    elif choice == "3":
        print("\n" + "=" * 60)
        print("ADDONS / OPTIONAL GROUPS")
        print("=" * 60)
        groups_list = list(addon_groups.items())
        for index, (group_name, group_files) in enumerate(groups_list, 1):
            print(f"{index} - {group_name} ({len(group_files)} files)")
        print("0 - Back")
        print("=" * 60)

        group_choice = input("\nChoose group: ").strip()
        if group_choice == "0":
            continue
        try:
            group_index = int(group_choice) - 1
            group_name, group_files = groups_list[group_index]
        except Exception:
            log("[ERROR] Invalid group selection.")
            continue

        print(f"\n{group_name}")
        for index, item in enumerate(group_files, 1):
            print(f"   {index} - {item['filename']}")

        print("\n1 - Send ALL files in this group")
        print("2 - Send SPECIFIC files")
        print("0 - Back")
        sub = input("Choice: ").strip()

        if sub == "1":
            selected = group_files
        elif sub == "2":
            nums = input("Enter numbers (example: 1/3/5 or 1 3 5): ").strip()
            nums_list = [int(v) for v in re.split(r"[,/;\s]+", nums) if v.isdigit()]
            selected = [group_files[n - 1] for n in nums_list if 1 <= n <= len(group_files)]
        else:
            continue
    else:
        log("[ERROR] Invalid choice.")
        continue

    if not selected:
        log("[ERROR] No files were selected.")
        continue

    show_preview(selected)
    confirm = input("\nSend to IDM? (Y/N): ").strip().upper()

    if confirm != "Y":
        log("[INFO] Operation cancelled by user.")
        continue

    print("\n" + "=" * 50)
    print("IDM ACTION")
    print("=" * 50)
    print("1 - Start downloading immediately")
    print("2 - Add to IDM queue only")
    print("0 - Back")
    print("=" * 50)
    action = input("Choice: ").strip()

    if action == "0":
        continue
    if action == "1":
        mode = "start"
        delay_input = input("Delay between each file (seconds) [default 2]: ").strip()
        try:
            start_delay = float(delay_input) if delay_input else 2.0
        except ValueError:
            start_delay = 2.0
    elif action == "2":
        mode = "queue"
        start_delay = 2.0
    else:
        log("[ERROR] Invalid action.")
        continue

    send_to_idm(selected, mode, start_delay)

    if input("\nClean temp files? (Y/N): ").strip().upper() == "Y":
        clean_temp_files()
    log("[OK] Operation completed successfully.")
    break


input("\nPress Enter to exit...")
