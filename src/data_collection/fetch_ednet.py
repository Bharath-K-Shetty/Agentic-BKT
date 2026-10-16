"""Download the two public archives linked by https://github.com/riiid/ednet.

python -m src.data_collection.fetch_ednet
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from zipfile import ZipFile

import requests

SOURCES = {
    "kt2": ("https://bit.ly/ednet-kt2", "EdNet-KT2.zip"),
    "contents": ("https://bit.ly/ednet-content", "contents.zip"),
}


class DownloadForm(HTMLParser):
    def __init__(self):
        super().__init__()
        self.action = None
        self.params = {}
        self.active = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form" and attrs.get("id") == "download-form":
            self.active = True
            self.action = attrs.get("action")
        if self.active and tag == "input" and attrs.get("name"):
            self.params[attrs["name"]] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.active = False


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url, path):
    with requests.Session() as session:
        resolved = session.get(url, timeout=60)
        resolved.raise_for_status()
        # Resolve the publisher's short URL rather than embedding a mirror ID.
        final = resolved.url
        if "drive.google.com/file/d/" not in final:
            raise ValueError(f"Unexpected official download location: {final}")
        ident = final.split("/file/d/", 1)[1].split("/", 1)[0]
        response = session.get("https://drive.google.com/uc", params={"export": "download", "id": ident}, stream=True, timeout=(30, 120))
        response.raise_for_status()
        if "text/html" in response.headers.get("Content-Type", ""):
            form = DownloadForm()
            form.feed(response.text)
            response.close()
            if form.action != "https://drive.usercontent.google.com/download":
                raise ValueError("Download unavailable: no public Google Drive confirmation form")
            response = session.get(form.action, params=form.params, stream=True, timeout=(30, 120))
            response.raise_for_status()
        if "text/html" in response.headers.get("Content-Type", ""):
            raise ValueError("Received an HTML page instead of the dataset archive")
        temporary = path.with_suffix(".zip.part")
        size = 0
        with response, temporary.open("wb") as f:
            for chunk in response.iter_content(1024 * 1024):
                f.write(chunk)
                size += len(chunk)
                if size % (50 * 1024 * 1024) < len(chunk):
                    print(f"{path.name}: {size / 1024**2:.0f} MiB", flush=True)
        with ZipFile(temporary) as archive:
            bad = archive.testzip()
            if bad:
                raise ValueError(f"Archive CRC failure: {bad}")
        temporary.replace(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=Path("data/raw/ednet"))
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    records = {}
    for key, (url, filename) in SOURCES.items():
        path = args.output / filename
        if not path.exists():
            download(url, path)
        with ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                raise ValueError(f"Archive CRC failure: {bad}")
            count = len(archive.namelist())
        records[key] = {"official_url": url, "file": filename, "bytes": path.stat().st_size,
                        "sha256": sha256(path), "archive_entries": count}
        print(f"Verified {filename}", flush=True)
    manifest = {"publisher": "https://github.com/riiid/ednet", "license": "CC BY-NC 4.0",
                "verified_at_utc": datetime.now(timezone.utc).isoformat(), "archives": records}
    (args.output / "download_manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
