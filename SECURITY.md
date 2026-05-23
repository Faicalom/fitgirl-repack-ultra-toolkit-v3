# Security Policy

## Release Scope

FitGirl Repack Ultra Toolkit v3 is maintained as a complete public project.
This repository is not an experimental sandbox and not a temporary prototype.

Its supported public release forms are:

- the source-and-batch project in this folder
- the packaged desktop installer release
  `FitGirl_Repack_Ultra_Toolkit_v3_Full_Shared_Setup.exe`

## Integrity Guidance

Users and publishers should verify the toolkit before distribution or use:

1. Compare published files against `checksums.sha256`.
2. Run `python toolkit_guard.py verify-checksums` in the source folder when
   using the batch edition.
3. Publish SHA-256 hashes together with any GitHub release asset.
4. Treat hash mismatches as a failed trust check.

## Source Edition

The batch edition is transparent and auditable because the workflow is present
as Python and batch source files in this repository.

Main integrity points:

- visible source for the extraction and resolver stages
- documented dependencies in `requirements.txt`
- runtime guard in `toolkit_guard.py`

## Packaged Release Guidance

For public end-user release, the preferred artifact is:

- `FitGirl_Repack_Ultra_Toolkit_v3_Full_Shared_Setup.exe`

This gives end users a cleaner install path while the repository continues to
serve as the source-based project edition.

## Security Expectations

This project should be presented publicly as a complete toolkit with release
artifacts, published hashes, and repository documentation.

If a release asset is unsigned, users should verify the published SHA-256 hash
before running it.
