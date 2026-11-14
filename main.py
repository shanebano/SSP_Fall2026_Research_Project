"""Run the whole pipeline: two CIS PDFs -> KDE YAMLs -> diffs -> Hadolint rules -> scan CSV.

Usage:
    python main.py docker-cis-v0.pdf docker-cis-v1.pdf --dockerfiles path/to/dockerfiles
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cisdiff import comparator, executor, extractor


def run(pdf1, pdf2, dockerfiles, out_dir="output", prompt="few-shot", hadolint="hadolint") -> Path:
    out = Path(out_dir) / f"{Path(pdf1).stem}_vs_{Path(pdf2).stem}"

    print("[Task-1] Reading PDFs and extracting KDEs with Gemma-3-1B")
    docs = extractor.load_documents(pdf1, pdf2)
    yamls, records = extractor.identify_kdes(docs, out, yaml_prompt=prompt, cache_dir=Path(out_dir) / ".cache")
    extractor.dump_llm_outputs(records, out / "llm_outputs.txt")

    print("[Task-2] Comparing KDE YAML files")
    k1, k2 = comparator.load_yaml_pair(*yamls)
    names = comparator.compare_element_names(k1, k2, out / "element_names_diff.txt")
    reqs = comparator.compare_element_requirements(k1, k2, out / "element_requirements_diff.txt")

    print("[Task-3] Mapping differences to Hadolint rules and scanning Dockerfiles")
    rules = executor.map_differences_to_rules(*executor.load_text_pair(names, reqs), out / "hadolint_rules.txt")
    df = executor.run_hadolint(rules, dockerfiles, hadolint_bin=hadolint)
    csv = executor.write_results_csv(df, out / "hadolint_results.csv")

    print(f"Done. Results in {out}/")
    return csv


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Detect CIS requirement changes and run Hadolint accordingly.")
    ap.add_argument("pdf1", help="first CIS benchmark PDF")
    ap.add_argument("pdf2", help="second CIS benchmark PDF")
    ap.add_argument("--dockerfiles", required=True, help="folder of Dockerfiles to scan (unzipped dockerfiles.zip)")
    ap.add_argument("--out", default="output", help="output folder (default: output)")
    ap.add_argument("--prompt", default="few-shot", choices=extractor.PROMPT_TYPES,
                    help="prompt type whose output becomes the YAML (default: few-shot)")
    ap.add_argument("--hadolint", default="hadolint", help="hadolint executable (default: hadolint on PATH)")
    a = ap.parse_args(argv)
    try:
        run(a.pdf1, a.pdf2, a.dockerfiles, a.out, a.prompt, a.hadolint)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()  # the frozen binary re-launches itself for helper processes
    sys.exit(main())
