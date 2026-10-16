"""Fetch pinned public evidence. Cached upstream files are not redistributed."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "research/solana/cache"
OUT = ROOT / "research/solana/cases/source_manifest.json"


def fetch(url):
    with urlopen(url, timeout=45) as response:
        return response.read()


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    anchor = "f6341296b9d909093b2fdda5072087d5157fa4e4"
    parent = "6801a5742e941dbf6f5f9b4ad5db65db28869ba3"
    sealevel = "24555d044802db4022112a94d6d70e74291a4b6d"
    crucible = json.loads(fetch("https://api.github.com/repos/asymmetric-research/crucible/commits/main"))["sha"]
    tasks = [
        ("anchor-return-data", "otter-sec/anchor", rev, path)
        for rev in [parent, anchor]
        for path in ["lang/syn/src/codegen/program/cpi.rs", "lang/attribute/program/src/declare_program/mods/cpi.rs"]
    ] + [
        ("anchor-return-data", "otter-sec/anchor", anchor, "tests/cpi-returns/tests/cpi-return.ts"),
        ("crucible-owner-mutation", "asymmetric-research/crucible", crucible, "docs/constraint-check-engine.md"),
        *[("sealevel-owner-check", "coral-xyz/sealevel-attacks", sealevel,
           f"programs/2-owner-checks/{variant}/src/lib.rs") for variant in ["insecure", "secure"]],
    ]

    def retrieve(task):
        case, repo, rev, path = task
        url = f"https://raw.githubusercontent.com/{repo}/{rev}/{path}"
        body = fetch(url)
        digest = sha256(body).hexdigest()
        (CACHE / digest).write_bytes(body)
        return {"case_id": case, "repository": repo, "revision": rev, "path": path,
                "url": url, "sha256": digest, "bytes": len(body)}

    with ThreadPoolExecutor(max_workers=4) as pool:
        files = list(pool.map(retrieve, tasks))
    result = {"retrieved_at": datetime.now(timezone.utc).isoformat(),
              "scope": "Source provenance only; no upstream program execution or independent adjudication.",
              "licensing": "Upstream code cached locally only; review upstream licenses before redistribution.",
              "files": files}
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Recorded {len(files)} pinned source files in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
