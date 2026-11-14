# Task-1 tests: one test per function. Gemma is replaced by a fake generator so CI needs no model.
import pytest
import yaml

from cisdiff import extractor as ex

REQS = "4.1 Ensure that a user for the container has been created\n4.6 Ensure that HEALTHCHECK instructions have been added"

CIS_TEXT = (
    "4.1 Ensure that a user for the container has been created (Automated)\nProfile Applicability:\n"
    "Level 1\n"
    "4.6 Ensure that HEALTHCHECK instructions have been added to\ncontainer images (Manual)\nProfile Applicability:\n"
)


def _pdf(path, line):
    """Write a one-line, one-page PDF that pypdf can read."""
    stream = f"BT /F1 12 Tf 72 720 Td ({line}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (i, body)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    path.write_bytes(bytes(out))
    return path


def test_load_documents(tmp_path):
    a = _pdf(tmp_path / "cis-a.pdf", "Ensure a user is created")
    docs = ex.load_documents(a, a)
    assert list(docs) == ["cis-a", "cis-a-2"]
    assert "Ensure a user is created" in docs["cis-a"]
    fake = tmp_path / "fake.pdf"
    fake.write_text("not a pdf")
    with pytest.raises(ValueError):
        ex.load_documents(fake, a)


def test_build_zero_shot_prompt():
    p = ex.build_zero_shot_prompt(REQS)
    assert isinstance(p, str) and REQS in p and "KDE:" in p and "Example" not in p


def test_build_few_shot_prompt():
    p = ex.build_few_shot_prompt(REQS)
    assert REQS in p and "Example answer" in p and "KDE: Docker daemon user" in p


def test_build_chain_of_thought_prompt():
    p = ex.build_chain_of_thought_prompt(REQS)
    assert REQS in p and "step by step" in p and "ANSWER" in p


def test_identify_kdes(tmp_path):
    def fake_gemma(prompt):
        return "KDE: Container user\nREQS: 4.1\nKDE: Healthcheck\nREQS: 4.6, 9.9"

    paths, records = ex.identify_kdes({"cis-r1": CIS_TEXT}, tmp_path, generate=fake_gemma)
    assert paths == [tmp_path / "cis-r1-kdes.yaml"]
    assert len(records) == 3
    assert yaml.safe_load(paths[0].read_text()) == {
        "element1": {"name": "Container user", "requirements": ["Ensure that a user for the container has been created"]},
        "element2": {"name": "Healthcheck",
                     "requirements": ["Ensure that HEALTHCHECK instructions have been added to container images"]},
    }


def test_dump_llm_outputs(tmp_path):
    rec = [{"document": "d", "prompt_type": "few-shot", "prompt": "P", "output": "O"}]
    text = ex.dump_llm_outputs(rec, tmp_path / "llm.txt").read_text()
    assert text.splitlines() == ["*LLM Name*", ex.LLM_NAME, "*Prompt Used*", "P", "*Prompt Type*", "few-shot",
                                 "*LLM Output*", "O"]
