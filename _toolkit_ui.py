# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 FaicalOm_DZ
#
# _toolkit_ui.py — UI helper called by FitGirl_Toolkit.bat
# Usage:
#   python _toolkit_ui.py init         — init/clear failed_links.txt with session header
#   python _toolkit_ui.py banner       — print colored banner
#   python _toolkit_ui.py progress     — animate red progress bar (reads fuckingfast_links.txt)
#   python _toolkit_ui.py end          — append session-end footer to failed_links.txt
#   python _toolkit_ui.py log_error X  — append error line to failed_links.txt

import sys
import os
import time
from datetime import datetime

# ── Enable ANSI on Windows ──────────────────────────────────────────────────
os.system("")
try:
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
except Exception:
    pass

R  = "\033[91m"   # bright red
G  = "\033[92m"   # bright green
Y  = "\033[93m"   # bright yellow
C  = "\033[96m"   # bright cyan
W  = "\033[97m"   # bright white
B  = "\033[1m"    # bold
D  = "\033[2m"    # dim
RS = "\033[0m"    # reset


# ─────────────────────────────────────────────────────────────────────────────

def cmd_init():
    with open("failed_links.txt", "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write(f"SESSION START : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("TOOLKIT       : FitGirl Repack Ultra Toolkit v3\n")
        f.write("=" * 70 + "\n\n")
    print(G + "[OK]" + RS + " Session log initialized  →  failed_links.txt")


def cmd_banner():
    w = 65
    top    = "╔" + "═" * w + "╗"
    mid    = "╠" + "═" * w + "╣"
    bot    = "╚" + "═" * w + "╝"
    blank  = "║" + " " * w + "║"

    def row(text):
        pad = w - len(text) - 2
        return "║  " + text + " " * pad + "║"

    print()
    print(C + top + RS)
    print(C + blank + RS)
    print(C + "║" + RS + B + Y + row("FitGirl Repack Ultra Toolkit  v3") + RS + C + RS)
    print(C + "║" + RS + D + row("Automated FuckingFast Downloader — github.com/FaicalOm_DZ") + C + RS)
    print(C + blank + RS)
    print(C + mid + RS)
    print(C + "║" + RS + D + row("  Stage 1  →  Extract links from page") + C + RS)
    print(C + "║" + RS + D + row("  Stage 2  →  Select files + resolve + send to IDM") + C + RS)
    print(C + blank + RS)
    print(C + bot + RS)
    print()


def cmd_progress():
    try:
        with open("fuckingfast_links.txt", "r", encoding="utf-8") as f:
            total = sum(1 for ln in f if ln.strip())
    except Exception:
        return

    if total == 0:
        return

    width = 52
    print(f"\n  {B}Found {C}{total}{RS}{B} FuckingFast link(s){RS}\n")

    for current in range(0, total + 1):
        pct   = current / total
        filled = int(width * pct)
        bar   = R + "█" * filled + D + "░" * (width - filled) + RS
        pstr  = f"{pct * 100:5.1f}%"
        sys.stdout.write(f"\r  [{bar}]  {B}{current:>3}/{total}{RS}  {pstr}")
        sys.stdout.flush()
        delay = max(0.02, min(0.10, 3.0 / total))
        time.sleep(delay)

    print(f"\n\n  {G}✓  All links ready — proceeding to Stage 2{RS}\n")


def cmd_end():
    with open("failed_links.txt", "a", encoding="utf-8") as f:
        f.write("\n" + "=" * 70 + "\n")
        f.write(f"SESSION END   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n")


def cmd_log_error(msg: str):
    with open("failed_links.txt", "a", encoding="utf-8") as f:
        ts = datetime.now().strftime("%H:%M:%S")
        f.write(f"[{ts}] [BAT][ERROR] {msg}\n")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""

    if cmd == "init":
        cmd_init()
    elif cmd == "banner":
        cmd_banner()
    elif cmd == "progress":
        cmd_progress()
    elif cmd == "end":
        cmd_end()
    elif cmd == "log_error":
        msg = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Unknown error"
        cmd_log_error(msg)
