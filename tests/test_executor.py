# Task-3 tests: one test per function
import pandas as pd
import pytest

from cisdiff import executor as ex
from cisdiff.comparator import NO_NAME_DIFF, NO_REQ_DIFF


def test_load_text_pair(tmp_path):
    n = tmp_path / "names.txt"
    r = tmp_path / "reqs.txt"
    n.write_text("Healthcheck\n\n")
    r.write_text("Healthcheck,Ensure HEALTHCHECK is added\n")
    assert ex.load_text_pair(n, r) == (["Healthcheck"], ["Healthcheck,Ensure HEALTHCHECK is added"])
    with pytest.raises(FileNotFoundError):
        ex.load_text_pair(tmp_path / "missing.txt", r)


def test_map_differences_to_rules(tmp_path):
    out = ex.map_differences_to_rules(["Container user"], ["Container user,Ensure user is non-root"], tmp_path / "a.txt")
    assert out.read_text().splitlines() == ["DL3002", "DL3004"]
    none = ex.map_differences_to_rules([NO_NAME_DIFF], [NO_REQ_DIFF], tmp_path / "b.txt")
    assert none.read_text().strip() == ex.NO_DIFF_FOUND
    nomap = ex.map_differences_to_rules(["Audit logging"], [], tmp_path / "c.txt")
    assert nomap.read_text().strip() == ex.NO_MAPPING_FOUND


def test_run_hadolint(tmp_path):
    d = tmp_path / "docker"
    d.mkdir()
    (d / "Dockerfile").write_text("FROM ubuntu\nRUN sudo apt-get install -y curl\nADD a /a\n")
    rules = tmp_path / "rules.txt"
    rules.write_text("DL3020\n")
    df = ex.run_hadolint(rules, d)
    assert list(df["RULEID"]) == ["DL3020"]
    rules.write_text(ex.NO_MAPPING_FOUND + "\n")
    assert {"DL3004", "DL3006", "DL3020"} <= set(ex.run_hadolint(rules, d)["RULEID"])


def test_write_results_csv(tmp_path):
    df = pd.DataFrame([
        {"FilePath": "a/Dockerfile", "RULEID": "DL3020", "DefaultSeverity": "error"},
        {"FilePath": "a/Dockerfile", "RULEID": "DL3020", "DefaultSeverity": "error"},
    ])
    out = ex.write_results_csv(df, tmp_path / "results.csv")
    assert out.read_text().splitlines() == ["FilePath,DefaultSeverity,RULEID,COUNT", "a/Dockerfile,error,DL3020,2"]
