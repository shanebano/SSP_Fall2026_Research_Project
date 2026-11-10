# Task-2 tests: one test per function
import pytest
import yaml

from cisdiff import comparator as comparator

A = {
    "element1": {"name": "Container user", "requirements": ["Ensure a user is created"]},
    "element2": {"name": "Healthcheck", "requirements": ["Ensure HEALTHCHECK is added"]},
}

B = {
    "element1": {"name": "Container user", 
                    "requirements": ["Ensure a user is created", "Ensure user is non-root"]},
    "element2": {"name": "Base image", "requirements": ["Ensure trusted base images"]},
    }

def _write(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(yaml.safe_dump(data))
    return p

def test_load_yaml_pair(tmp_path):
    k1, k2 = cmp.test_load_yaml_pair(_write(tmp_path, "a-kdes.yaml",A), _write(tmp_path, "b-kdes.yaml", B))
    assert k1["element1"]["name"] == "Container user"
    assert len(k2) == 2
    bad = tmp_path / "bad.yaml"
    bad.write_text("- just\n- a list\n")
    with pytest.raises(ValueError):
        cmp.test_load_yaml_pair(bad, bad)

def test_compare_element_names(tmp_path):
    out = cmp.compare_element_names(A, B, tmp_path / "names.txt")
    assert out.read_text().splitlines() == ["Base image", "Healthcheck"]
    same = cmp.compare_element_names(A, A, tmp_path / "same.txt")
    assert same.read_text().strip() == cmp.NO_NAME_DIFF


def test_compare_element_requirements(tmp_path):
    out = cmp.compare_element_requirements(A, B, tmp_path / "reqs.txt")
    assert out.read_text().splitlines() == [
        "Base image,Ensure trusted base images",
        "Container user,Ensure user is non-root",
        "Healthcheck,Ensure HEALTHCHECK is added",
    ]
    same = cmp.compare_element_requirements(B, B, tmp_path / "same.txt")
    assert same.read_text().strip() == cmp.NO_REQ_DIFF
