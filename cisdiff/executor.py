# Task-3 Executor

# Four required functions:
    # load_text_pair
    # map_differences_to_rules
    # run_hadolint
    # write_results_csv


from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple

import pandas as pd

from cisdiff.comparator import NO_NAME_DIFF, NO_REQ_DIFF

NO_DIFF_FOUND = "NO DIFFERENCES FOUND"
NO_MAPPING_FOUND = "NO MAPPING FOUND"
CSV_HEADERS = ["FilePath", "DefaultSeverity", "RULEID", "COUNT"]

# CIS Docker Benchmark section 4 (Dockerfile) topics -> Hadolint rules.
# A difference line maps to a rule when it contains any of the keywords.
RULE_MAP = [
    (("user", "root"), ["DL3002"]),
    (("sudo",), ["DL3004"]),
    (("base image", "trusted image", "image tag", "tag"), ["DL3006", "DL3007"]),
    (("healthcheck", "health check"), ["DL3057"]),
    (("add instruction", "copy instead", " copy ", " add "), ["DL3020"]),
    (("update instruction", "apt-get update", "update alone", "cache"), ["DL3009", "DL3059"]),
    (("verified package", "pin", "package version", "package"), ["DL3008", "DL3013", "DL3016", "DL3018"]),
    (("expose", "port"), ["DL3011"]),
    (("shell", "pipefail"), ["DL4006"]),
]


def load_text_pair(names_path, reqs_path) -> Tuple[List[str], List[str]]:
    """Function 1: load the two TEXT files produced by Task-2."""
    out = []
    for raw in (names_path, reqs_path):
        p = Path(raw)
        if not p.is_file():
            raise FileNotFoundError(f"TEXT file not found: {p}")
        if p.suffix.lower() != ".txt":
            raise ValueError(f"Expected a .txt file, got: {p.name}")
        out.append([ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()])
    return out[0], out[1]


def map_differences_to_rules(names: List[str], reqs: List[str], out_path) -> Path:
    """Function 2: write the Hadolint rules that map to the Task-2 differences."""
    diffs = [ln for ln in names + reqs if ln not in (NO_NAME_DIFF, NO_REQ_DIFF)]
    if not diffs:
        body = NO_DIFF_FOUND
    else:
        rules = set()
        for line in diffs:
            text = f" {line.lower().replace(',', ' ')} "
            for keywords, codes in RULE_MAP:
                if any(k in text for k in keywords):
                    rules.update(codes)
        body = "\n".join(sorted(rules)) if rules else NO_MAPPING_FOUND
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body + "\n", encoding="utf-8")
    return out_path


def run_hadolint(rules_path, dockerfiles_dir, hadolint_bin: str = "hadolint") -> pd.DataFrame:
    """Function 3: run Hadolint on every Dockerfile under dockerfiles_dir.

    All rules run when the rules file says NO DIFFERENCES FOUND / NO MAPPING FOUND,
    otherwise only the listed rules are kept.
    """
    exe = shutil.which(hadolint_bin)
    if exe is None:
        raise FileNotFoundError(f"Hadolint executable not found: {hadolint_bin}")
    root = Path(dockerfiles_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Dockerfile directory not found: {root}")

    lines = [ln.strip() for ln in Path(rules_path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    selected = set() if lines in ([NO_DIFF_FOUND], [NO_MAPPING_FOUND]) else set(lines)

    files = sorted(p for p in root.rglob("*") if p.is_file() and "dockerfile" in p.name.lower())
    rows = []
    for f in files:
        proc = subprocess.run([exe, "--no-fail", "-f", "json", str(f)], capture_output=True, text=True)
        for item in json.loads(proc.stdout or "[]"):
            if not selected or item["code"] in selected:
                rows.append({"FilePath": str(f), "RULEID": item["code"], "DefaultSeverity": item["level"],
                             "Line": item["line"], "Message": item["message"]})
    return pd.DataFrame(rows, columns=["FilePath", "RULEID", "DefaultSeverity", "Line", "Message"])


def write_results_csv(df: pd.DataFrame, out_path) -> Path:
    """Function 4: write FilePath, DefaultSeverity, RULEID, COUNT per file and rule."""
    summary = (df.groupby(["FilePath", "DefaultSeverity", "RULEID"]).size().reset_index(name="COUNT")
               if not df.empty else pd.DataFrame(columns=CSV_HEADERS))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary[CSV_HEADERS].to_csv(out_path, index=False)
    return out_path
