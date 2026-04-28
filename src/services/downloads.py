"""Helpers for downloading and caching service binaries."""

from __future__ import annotations

import shutil
import tarfile
import urllib.request
import zipfile
from pathlib import Path


def download_file(url: str, destination: Path) -> Path:
    """Download a file into the local cache if it is missing."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination

    with urllib.request.urlopen(url) as response, destination.open("wb") as file_obj:
        shutil.copyfileobj(response, file_obj)
    return destination


def extract_tar_member(archive_path: Path, member_suffix: str, destination: Path) -> Path:
    """Extract one file from a tar archive by path suffix."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination

    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            if member.isfile() and member.name.endswith(member_suffix):
                extracted = archive.extractfile(member)
                if extracted is None:
                    break
                with destination.open("wb") as file_obj:
                    shutil.copyfileobj(extracted, file_obj)
                destination.chmod(0o755)
                return destination

    raise FileNotFoundError(f"Could not find '{member_suffix}' in {archive_path}")


def extract_zip_member(archive_path: Path, member_suffix: str, destination: Path) -> Path:
    """Extract one file from a zip archive by path suffix."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination

    with zipfile.ZipFile(archive_path) as archive:
        for member_name in archive.namelist():
            if member_name.endswith(member_suffix):
                with archive.open(member_name) as extracted, destination.open("wb") as file_obj:
                    shutil.copyfileobj(extracted, file_obj)
                destination.chmod(0o755)
                return destination

    raise FileNotFoundError(f"Could not find '{member_suffix}' in {archive_path}")
