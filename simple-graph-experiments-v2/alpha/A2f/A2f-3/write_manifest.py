from __future__ import annotations

import csv
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
MANIFEST = RESULTS / "artifact_manifest.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    files = sorted(path for path in RESULTS.rglob("*") if path.is_file() and path != MANIFEST)
    with MANIFEST.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("path", "bytes", "sha256"))
        for path in files:
            writer.writerow((path.relative_to(RESULTS).as_posix(), path.stat().st_size, sha256(path)))
    print(f"manifest_rows={len(files)} sha256={sha256(MANIFEST)}")


if __name__ == "__main__":
    main()
