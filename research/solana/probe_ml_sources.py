"""Read-only, bounded provenance probe for the proposed blockchain ML study.

Fetch public documentation and JSON records only. No training, upstream code
execution, private keys, cluster calls or multi-GB archive download.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/raw/solana_ml_probe"
OUTPUT = ROOT / "docs/results/blockchain_ml_source_probe.json"
MAX_BYTES = 20_000_000
GH = "https://raw.githubusercontent.com"
HF = "https://huggingface.co/datasets"
MELT = "0732bcfab54f508c27becd6d9b2b10b1b6ac2517"
NEIGHBOR = "12c7fb5a0ab65b9fb19bc237e66790c83288103e"
SOLRPDS = "43416d75d2c82d09c6c6e9221ba730f5c8440211"
CORPUS = "13bec2bf3089d56d50c35e602616d1b993bb37f5"
TRENCHES = "0a38dff884ba41f63da325d04fc85521b1cb34fe"


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    tasks = []
    for repo, rev, paths in [
        ("git-disl/MELT", MELT, ["README.md", "LICENSE", "src/dataset.py", "src/feat_gen.py",
                                "data/memecoin/memecoin_list.jsonl"]),
        ("Gauravpoudel7/AI_RugPull_Prediction", NEIGHBOR,
         ["README.md", "PROVENANCE.md", "scripts/protocol.py", "scripts/models.py",
          "scripts/uncertainty.py", "docs/process/audit_report.md"]),
        ("DeFiLabX/SolRPDS", SOLRPDS, ["README.md", "dataset/json/2021.json"]),
    ]:
        tasks.extend((repo, rev, p, f"{GH}/{repo}/{rev}/{p}") for p in paths)
    for repo, rev, paths in [
        ("Slinky21/Pumpfun_Memecoin_Corpus", CORPUS, ["README.md", "KNOWN_ISSUES.md"]),
        ("Tr4m0ryp/trenches-pumpfun-forward-2026-08", TRENCHES,
         ["README.md", "DATASHEET.md", "MANIFEST.json"]),
    ]:
        tasks.extend((repo, rev, p, f"{HF}/{repo}/resolve/{rev}/{p}") for p in paths)

    def retrieve(task):
        repo, rev, path, url = task
        with urlopen(url, timeout=45) as response:
            body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError(f"Bound exceeded for {url}")
        digest = sha256(body).hexdigest()
        (CACHE / digest).write_bytes(body)
        record = {"repository": repo, "revision": rev, "path": path,
                  "url": url, "bytes": len(body), "sha256": digest,
                  "download_complete": True}
        if path.endswith("memecoin_list.jsonl"):
            rows = [json.loads(line) for line in body.splitlines() if line.strip()]
            creators = {r.get("creator") for r in rows}
            record["json_observations"] = {
                "rows": len(rows), "first_record_fields": sorted(rows[0]),
                "distinct_creator_values": len(creators),
                "creator_values_if_at_most_ten": sorted(creators) if len(creators) <= 10 else None,
                "timestamp_field_semantics": "Migration records per paper section 3.1, not verified original token creators or launch timestamps",
            }
        if path == "dataset/json/2021.json":
            data = json.loads(body)
            if isinstance(data, list):
                record["json_observations"] = {"rows": len(data), "first_record_fields": sorted(data[0])}
            else:
                record["json_observations"] = {"top_level_type": type(data).__name__,
                                               "top_level_keys": sorted(data)[:20]}
        return record

    with ThreadPoolExecutor(max_workers=4) as pool:
        files = list(pool.map(retrieve, tasks))
    report = {"retrieved_at": datetime.now(timezone.utc).isoformat(),
              "scope": "Pinned documentation/code reads and JSON schema/count probe. No model trained or upstream performance reproduced; no parquet contents or Drive archives fetched.",
              "cache": str(CACHE.relative_to(ROOT)), "files": files}
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Recorded {len(files)} pinned sources in {OUTPUT.relative_to(ROOT)}")
    for record in files:
        if "json_observations" in record:
            print(record["repository"], json.dumps(record["json_observations"]))


if __name__ == "__main__":
    main()
