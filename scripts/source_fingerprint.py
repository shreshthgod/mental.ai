"""Content fingerprint of source/configuration/corpora, excluding secrets/data.

The declared scope includes frontend source so pre-existing changes are covered.
Reports/handoff are excluded to avoid self-referential hashes. Model artifacts
are hashed separately, without deserializing or reading raw datasets.
"""
import hashlib
import json
from pathlib import Path


def fingerprint(root: str | Path) -> dict:
    root = Path(root)
    paths = set()
    for directory in ("api", "tests", "scripts", "web/src", "web/scripts",
                      "supabase", "evaluation", "Step 12 - Packaging/package/mental_health_screening"):
        base = root / directory
        if base.exists():
            paths.update(p for p in base.rglob("*") if p.is_file()
                         and p.suffix in {".py", ".ts", ".tsx", ".css", ".mjs", ".sql", ".json"}
                         and "__pycache__" not in p.parts)
    for name in ("Dockerfile", ".env.example", "api/requirements.txt",
                 "api/requirements-runtime.txt",
                 "main.py", "requirements.txt", ".gitignore", "start-dev.sh", "package.json", "package-lock.json",
                 "Step 12 - Packaging/package/requirements.txt", "web/package.json",
                 "web/package-lock.json", "web/vite.config.ts", "vercel.json",
                 "evaluation/requirements-semantic.txt"):
        p = root / name
        if p.is_file():
            paths.add(p)
    manifest = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(paths)}
    artifacts = root / "Step 12 - Packaging/package/mental_health_screening/artifacts"
    model_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(artifacts.glob("*")) if p.is_file()}
    return {"source_sha256": hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "scope": "source/configuration/corpora; excludes reports, documentation, secrets, raw data",
        "manifest": manifest, "artifacts": model_hashes}


if __name__ == "__main__":
    print(json.dumps(fingerprint(Path(__file__).resolve().parents[1]), indent=2))
