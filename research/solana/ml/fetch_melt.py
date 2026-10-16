"""Fetch the author's public parsed pre-migration release, never raw/pickle code.

Uses curl because Python TLS failed in the local environment. The normal Drive
large-file confirmation form is followed; no login or access restriction bypass.
"""
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import subprocess
from urllib.parse import urlencode
import zipfile

ROOT = Path(__file__).resolve().parents[3]
REV = "0732bcfab54f508c27becd6d9b2b10b1b6ac2517"
FILE_ID = "1rqzkaVoc1FG8XRp-hBxECjiG_PxAn5Cp"


class Confirmation(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fields = {}

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "input" and values.get("type") == "hidden":
            self.fields[values["name"]] = values.get("value", "")


def fetch(url, path, timeout=900):
    subprocess.run(["curl", "-L", "--fail", "--retry", "2", "--max-time", str(timeout),
                    "--output", str(path), url], check=True)


def ranged_archive(url, archive):
    """Bounded byte ranges retain completed parts when a large transfer stalls."""
    parts = archive.parent / "archive_parts"
    parts.mkdir(exist_ok=True)
    headers, probe = parts / "probe.headers", parts / "probe.bin"
    subprocess.run(["curl", "-sS", "-L", "--fail", "--max-time", "30", "-r", "0-99",
                    "-D", str(headers), "-o", str(probe), url], check=True)
    match = re.search(r"content-range: bytes 0-99/(\d+)", headers.read_text(), re.I)
    if not match or probe.stat().st_size != 100:
        raise RuntimeError("Server did not honor byte range")
    total = int(match[1])
    chunk = 256 * 1024 * 1024

    def one(start):
        end = min(start + chunk, total) - 1
        path = parts / f"{start}.part"
        expected = end - start + 1
        for attempt in range(5):
            size = path.stat().st_size if path.exists() else 0
            if size == expected:
                return path
            if size > expected:
                raise RuntimeError("Oversized cached part")
            tmp, hdr = parts / f"{start}.incoming", parts / f"{start}.headers"
            result = subprocess.run(["curl", "-sS", "-L", "--fail", "--max-time", "60",
                                     "-r", f"{start + size}-{end}", "-D", str(hdr), "-o", str(tmp), url])
            expected_header = f"content-range: bytes {start + size}-{end}/{total}"
            if expected_header not in hdr.read_text().lower():
                raise RuntimeError("Range identity changed or was not honored")
            if tmp.exists():
                with path.open("ab") as out, tmp.open("rb") as incoming:
                    for b in iter(lambda: incoming.read(1024 * 1024), b""):
                        out.write(b)
                tmp.unlink()
            print(f"range {start}: {path.stat().st_size}/{expected} bytes; curl={result.returncode}", flush=True)
        if path.stat().st_size != expected:
            raise RuntimeError("Range incomplete after bounded retries; partial bytes retained")
        return path

    with ThreadPoolExecutor(max_workers=4) as pool:
        paths = list(pool.map(one, range(0, total, chunk)))
    with archive.open("wb") as out:
        for path in paths:
            with path.open("rb") as incoming:
                for b in iter(lambda: incoming.read(1024 * 1024), b""):
                    out.write(b)
    if archive.stat().st_size != total:
        raise RuntimeError("Combined archive size mismatch")


def main():
    raw = ROOT / "data/raw/melt"
    raw.mkdir(parents=True, exist_ok=True)
    fetch(f"https://raw.githubusercontent.com/git-disl/MELT/{REV}/data/label/label.csv",
          raw / "label.csv", 60)
    archive = raw / "pre_migration_tx.zip"
    if archive.exists() and zipfile.is_zipfile(archive):
        print("Existing ZIP retained; experiment records its content hash.")
        return
    confirmation = raw / "download.html"
    fetch("https://drive.usercontent.google.com/download?" + urlencode({"id": FILE_ID, "export": "download"}),
          confirmation, 60)
    parser = Confirmation()
    parser.feed(confirmation.read_text())
    if parser.fields.get("id") != FILE_ID or parser.fields.get("confirm") != "t":
        raise RuntimeError("Expected public large-file confirmation unavailable; archive not fetched")
    ranged_archive("https://drive.usercontent.google.com/download?" + urlencode(parser.fields), archive)
    if not zipfile.is_zipfile(archive):
        raise RuntimeError("Download is not a valid ZIP")


if __name__ == "__main__":
    main()
