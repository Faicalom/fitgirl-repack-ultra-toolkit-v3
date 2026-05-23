# FitGirl Repack Ultra Toolkit v3

FitGirl Repack Ultra Toolkit v3 is a complete Windows toolkit for extracting
page links, resolving final download URLs, organizing game parts and add-ons,
and sending the selected files to Internet Download Manager (IDM).

This is a full project prepared for real public use. It is not a throwaway
demo, not a temporary prototype, and not an experimental placeholder.

## Project Status

- Public-facing Windows project
- Stable batch workflow included in this folder
- Documentation, license, integrity hashes, and runtime checks included
- Suitable for GitHub publication as a real maintained toolkit

## Recommended Public Release

The recommended packaged release for end users is:

- `FitGirl_Repack_Ultra_Toolkit_v3_Full_Shared_Setup.exe`

That installer is intended for users who want a ready-to-install desktop
release without working directly with the Python source files.

## What This Folder Contains

This folder is the source-and-batch edition of the project. It includes:

- `FitGirl_Toolkit.bat`
  the main batch launcher
- `Page_Link_Extractor.py` and `Page_Link_Extractor_speed.py`
  stage 1 extraction logic
- `Direct_Link_Resolver.py` and `Direct_Link_Resolver_Slow.py`
  direct-link resolution logic
- `Download_Manager_Sender.py` and `Download_Manager_Sender_Speed.py`
  IDM integration and file-selection flow
- `_toolkit_ui.py`
  console UI helper
- `toolkit_guard.py`
  runtime and integrity checks
- `checksums.sha256`
  published file hashes for verification

## Usage Modes

There are two valid ways to publish or use the toolkit:

1. Source + batch mode
   Users download this project folder, install the Python requirements, and run
   `FitGirl_Toolkit.bat`.
2. Packaged installer mode
   Users download `FitGirl_Repack_Ultra_Toolkit_v3_Full_Shared_Setup.exe` and
   install the desktop application directly.

## Batch Workflow

Install dependencies:

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

Run the batch version:

```powershell
.\FitGirl_Toolkit.bat
```

Optional runtime check:

```powershell
python toolkit_guard.py runtime-check
```

## Integrity

This project includes integrity support for public publishing:

- `checksums.sha256` for published file verification
- `toolkit_guard.py verify-checksums` for local validation
- auditable Python source files for the batch workflow

## Repository Quality

This repository is organized as a real project:

- clear launcher entry point
- documented dependencies
- license file included
- security guidance included
- reproducible script workflow
- release-oriented structure instead of a scratch or test-only folder

## License

This project is distributed under GPL-3.0-or-later. See `LICENSE`.
