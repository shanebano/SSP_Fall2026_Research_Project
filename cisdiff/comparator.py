# Task-2 Comparator 

#Three required functions:

    #load_yaml_pair
    #compare_element_names
    #compare_element_requirements


from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set, Tuple

import yaml

NO_NAME_DIFF = "NO DIFFERENCES IN REGARDS TO ELEMENT NAMES"
NO_REQ_DIFF = "NO DIFFERENCES IN REGARDS TO ELEMENT REQUIREMENTS"

KDEs = Dict[str, dict]


def _validate_kdes(data, path: Path) -> KDEs:
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a mapping of elements")
    for key, el in data.items():
        if not isinstance(el, dict) or "name" not in el:
            raise ValueError(f"{path}: element '{key}' must have a 'name' field")
        reqs = el.get("requirements") or []
        if not isinstance(reqs, list):
            raise ValueError(f"{path}: element '{key}' requirements must be a list")
        el["requirements"] = [str(r) for r in reqs]
    return data


def load_yaml_pair(path1, path2) -> Tuple[KDEs, KDEs]:
    """Function 1: load and validate the two YAML files produced by Task-1."""
    out = []
    for raw in (path1, path2):
        p = Path(raw)
        if not p.is_file():
            raise FileNotFoundError(f"YAML file not found: {p}")
        if p.suffix.lower() not in (".yaml", ".yml"):
            raise ValueError(f"Expected a .yaml/.yml file, got: {p.name}")
        with open(p, encoding="utf-8") as fh:
            try:
                data = yaml.safe_load(fh)
            except yaml.YAMLError as exc:
                raise ValueError(f"Invalid YAML in {p}: {exc}") from exc
        out.append(_validate_kdes(data, p))
    return out[0], out[1]


def _names(kdes: KDEs) -> Set[str]:
    return {str(el["name"]).strip() for el in kdes.values()}


def _pairs(kdes: KDEs) -> Set[Tuple[str, str]]:
    return {
        (str(el["name"]).strip(), str(r).strip())
        for el in kdes.values()
        for r in el.get("requirements") or []
    }


def compare_element_names(kdes1: KDEs, kdes2: KDEs, out_path) -> Path:
    """Function 2: write KDE names present in only one of the two files."""
    diff = sorted(_names(kdes1) ^ _names(kdes2))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(("\n".join(diff) if diff else NO_NAME_DIFF) + "\n", encoding="utf-8")
    return out_path


def compare_element_requirements(kdes1: KDEs, kdes2: KDEs, out_path) -> Path:
    """Function 3: write NAME,REQU tuples that are in only one of the two files.

    Covers both a KDE that exists in only one file (all its requirements are
    listed) and a KDE in both files whose requirements changed.
    """
    diff: List[Tuple[str, str]] = sorted(_pairs(kdes1) ^ _pairs(kdes2))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"{n},{r}" for n, r in diff) if diff else NO_REQ_DIFF
    out_path.write_text(body + "\n", encoding="utf-8")
    return out_path
