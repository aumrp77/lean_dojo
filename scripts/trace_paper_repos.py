#!/usr/bin/env python3
"""
Trace the fixed set of paper repos and materialize corpus.jsonl
next to RAID/data/<name>_<commit>/, mirroring the manual veil flow.

Run from repo root:
    export RAID_DIR="$PWD/RAID"
    export REPO_DIR="$RAID_DIR/repos"
    python scripts/trace_paper_repos.py
"""

import os
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()
REPO_ROOT = HERE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lean_dojo import LeanGitRepo  # noqa: E402
from lean_dojo.data_extraction.trace import get_traced_repo_path  # noqa: E402


# hardcoded list reconstructed from the paper / convo
# ==== Already traced ====
# 1. teorth/pfr FAITHFUL
# 2. avigad/mathematics_in_lean_source
# 3. yangky11/miniF2F-lean4
# 6. AlexKontorovich/PrimeNumberTheoremAnd
# 7. dwrensha/compfiles
# 8. ImperialCollegeLondon/FLT
# 9. verse-lab/veil
# 10. eric-wieser/lean-matrix-cookbook

# ==== Heavy / needs fix ====
# 4. lecopivo/SciLean (macOS SG_READ_ONLY crash)
# 11. loganrjmurphy/LeanEuclid (same)

# ==== Remaining targets ====
# PAPER_REPOS = [
#     {
#         "owner": "dwrensha",
#         "name": "compfiles",
#         "sha": "f99bf6f2928d47dd1a445b414b3a723c2665f091",
#     },
#     {
#         "owner": "avigad",
#         "name": "mathematics_in_lean_source",
#         "sha": "5297e0fb051367c48c0a084411853a576389ecf5",
#     },
#     {
#         "owner": "yangky11",
#         "name": "miniF2F-lean4",
#         "sha": "9e445f5435407f014b88b44a98436d50dd7abd00",
#     },
#     {
#         "owner": "teorth",
#         "name": "pfr",
#         "sha": "fa398a5b853c7e94e3294c45e50c6aee013a2687",
#     },
#     {
#         "owner": "ImperialCollegeLondon",
#         "name": "FLT",
#         "sha": "b208a302cdcbfadce33d8165f0b054bfa17e2147",
#     },
#     {
#         "owner": "verse-lab",
#         "name": "veil",
#         "sha": "a9fe7205c57f7b6ee8b350bfc87b9b4b28c57781",
#     },
# ]

PAPER_REPOS = [
    {
        "owner": "lecopivo",
        "name": "SciLean",
        "sha": "22d53b2f4e3db2a172e71da6eb9c916e62655744",
    },
    {
        "owner": "loganrjmurphy",
        "name": "LeanEuclid",
        "sha": "f1912c3090eb82820575758efc31e40b9db86bb8",
    },
    {
        "owner": "FormalizedFormalLogic",
        "name": "Foundation",
        "sha": "d5fe5d057a90a0703a745cdc318a1b6621490c21",
    },
#     {
#         "owner": "TODO",
#         "name": "lean4lean",
#         "sha": "05b1f4a68c5facea96a5ee51c6a56fef21276e0f",
#     },
]


def make_corpus_from_repo(source_root: pathlib.Path, out_dir: pathlib.Path, url: str, commit: str) -> int:
    """Scan .lake/build/ir for *.ast.json and write corpus.jsonl."""
    ir_root = source_root / ".lake" / "build" / "ir"
    if not ir_root.exists():
        print(f"  !! no .lake/build/ir in {source_root}, skipping corpus.jsonl")
        return 0

    recs = []
    for p in ir_root.rglob("*.ast.json"):
        recs.append(
            {
                "repo_url": url,
                "commit": commit,
                "ast_path": str(p.relative_to(source_root)),
            }
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "corpus.jsonl"
    with out_file.open("w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    print(f"  wrote {len(recs)} records to {out_file}")
    return len(recs)


def main() -> None:
    raid_dir = os.environ.get("RAID_DIR")
    repo_dir = os.environ.get("REPO_DIR")

    if not raid_dir or not repo_dir:
        raise SystemExit("Please set RAID_DIR and REPO_DIR before running.")

    raid_dir = pathlib.Path(raid_dir)
    repo_dir = pathlib.Path(repo_dir)

    for item in PAPER_REPOS:
        url = f"https://github.com/{item['owner']}/{item['name']}"
        commit = item["sha"]

        print(f"\n=== tracing {url}@{commit} ===")
        try:
            repo = LeanGitRepo(url, commit)
            traced_path = get_traced_repo_path(repo, build_deps=True)
            traced_path = pathlib.Path(traced_path)
            print(f"  lean_dojo traced into cache: {traced_path}")
        except Exception as e:
            print(f"  !! lean_dojo failed for {url}@{commit}: {e}")
            continue

        # repo as checked out by the earlier crawl
        repo_root = repo_dir / item["owner"] / item["name"]
        out_dir = raid_dir / "data" / f"{item['name']}_{commit}"

        if not repo_root.exists():
            print(f"  !! repo root {repo_root} not found — was it cloned under RAID/repos/?")

        sources = [traced_path]
        if repo_root.exists():
            sources.append(repo_root)

        exported = 0
        for src in sources:
            exported = make_corpus_from_repo(src, out_dir, url, commit)
            if exported > 0:
                break

        if exported > 0:
            print(f"  ✅ exported corpus for {item['name']} ({exported} files)")
        else:
            print(f"  ⚠ traced but no IR — likely a build/env issue for this repo")

    print("\nDONE.")


if __name__ == "__main__":
    main()
