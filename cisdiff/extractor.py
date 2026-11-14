# Task-1 Extractor

# Six required functions:
    # load_documents
    # build_zero_shot_prompt
    # build_few_shot_prompt
    # build_chain_of_thought_prompt
    # identify_kdes
    # dump_llm_outputs


from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import yaml

MODEL_ID = "google/gemma-3-1b-it"
LLM_NAME = "Gemma-3-1B (google/gemma-3-1b-it)"
PROMPT_TYPES = ("zero-shot", "few-shot", "chain-of-thought")
MAX_PDF_BYTES = 50 * 1024 * 1024
CHUNK_SIZE = 12  # requirements per prompt; keeps Gemma-3-1B within a short, reliable context

# A recommendation header in a CIS benchmark, e.g.
# "4.1 Ensure that a user for the container has been created (Automated)\nProfile Applicability:"
_HEADER = re.compile(
    r"^(\d+(?:\.\d+)+)\s+((?:(?!\n\d+\.\d).)+?)\s*\((?:Manual|Automated)\)\s*\n\s*Profile Applicability",
    re.M | re.S,
)

_TASK = (
    "You are a security analyst reading the CIS Docker Benchmark. Below is a numbered list of "
    "security requirements. Group them into key data elements (KDEs). A KDE is the Docker "
    "component or setting the requirements protect, for example a container user, a base image "
    "or the Docker daemon. One KDE can map to several requirements. Every requirement number must "
    "appear exactly once."
)

_FORMAT = (
    "Answer only in this format, one block per KDE:\n"
    "KDE: <short name of the element>\n"
    "REQS: <comma separated requirement numbers>"
)

_EXAMPLE_IN = (
    "2.1 Run the Docker daemon as a non-root user, if possible\n"
    "2.2 Ensure network traffic is restricted between containers on the default bridge\n"
    "2.3 Ensure the logging level is set to 'info'\n"
    "2.4 Ensure Docker is allowed to make changes to iptables"
)

_EXAMPLE_OUT = (
    "KDE: Docker daemon user\nREQS: 2.1\n"
    "KDE: Container network\nREQS: 2.2, 2.4\n"
    "KDE: Daemon logging\nREQS: 2.3"
)

Generator = Callable[[str], str]
Requirement = Tuple[str, str]  # (number, title)


def load_documents(path1, path2) -> Dict[str, str]:
    """Function 1: validate the two PDF inputs and return {document name: text}."""
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    docs: Dict[str, str] = {}
    for raw in (path1, path2):
        p = Path(raw)
        if not p.is_file():
            raise FileNotFoundError(f"PDF file not found: {p}")
        if p.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a .pdf file, got: {p.name}")
        size = p.stat().st_size
        if size == 0 or size > MAX_PDF_BYTES:
            raise ValueError(f"{p.name}: file size {size} bytes is outside the allowed range")
        with open(p, "rb") as fh:
            if fh.read(5) != b"%PDF-":
                raise ValueError(f"{p.name}: not a PDF document")
        logging.getLogger("pypdf").setLevel(logging.ERROR)
        try:
            text = "\n".join(page.extract_text() or "" for page in PdfReader(p).pages)
        except PdfReadError as exc:
            raise ValueError(f"{p.name}: unreadable PDF: {exc}") from exc
        if not text.strip():
            raise ValueError(f"{p.name}: no extractable text")
        name = p.stem
        if name in docs:  # same file given twice (e.g. v1 vs v1): keep both entries distinct
            name = f"{name}-2"
        docs[name] = text
    return docs


def _requirements(text: str) -> List[Requirement]:
    """Pull every numbered recommendation title out of a CIS benchmark's text."""
    text = re.sub(r"Page \d+\s*\n", "", text)
    seen, out = set(), []
    for num, title in _HEADER.findall(text):
        if num not in seen:
            seen.add(num)
            out.append((num, " ".join(title.split())))
    return out


def _chunks(reqs: List[Requirement]) -> List[List[Requirement]]:
    """Split per top-level CIS section, then into CHUNK_SIZE pieces, so a requirement added in
    one section does not shift the prompts (and Gemma's groupings) of every other section."""
    sections: Dict[str, List[Requirement]] = {}
    for r in reqs:
        sections.setdefault(r[0].split(".")[0], []).append(r)
    return [sec[i:i + CHUNK_SIZE] for sec in sections.values() for i in range(0, len(sec), CHUNK_SIZE)]


def _numbered(reqs: List[Requirement]) -> str:
    return "\n".join(f"{n} {t}" for n, t in reqs)


def build_zero_shot_prompt(requirements_text: str) -> str:
    """Function 2: zero-shot prompt for one block of numbered requirements."""
    return f"{_TASK}\n\n{_FORMAT}\n\nRequirements:\n{requirements_text}"


def build_few_shot_prompt(requirements_text: str) -> str:
    """Function 3: few-shot prompt with one worked example."""
    return (
        f"{_TASK}\n\n{_FORMAT}\n\n"
        f"Example requirements:\n{_EXAMPLE_IN}\n\nExample answer:\n{_EXAMPLE_OUT}\n\n"
        f"Requirements:\n{requirements_text}"
    )


def build_chain_of_thought_prompt(requirements_text: str) -> str:
    """Function 4: chain-of-thought prompt that asks for reasoning before the answer."""
    return (
        f"{_TASK}\n\n"
        "Think step by step. First, for each requirement, write one short line naming the Docker "
        "component it is about. Second, merge requirements that are about the same component. "
        "Third, write the final answer after a line that says ANSWER.\n\n"
        f"{_FORMAT}\n\nRequirements:\n{requirements_text}"
    )


PROMPT_BUILDERS = {
    "zero-shot": build_zero_shot_prompt,
    "few-shot": build_few_shot_prompt,
    "chain-of-thought": build_chain_of_thought_prompt,
}

_pipe = None


def gemma_generate(prompt: str) -> str:
    """Run Gemma-3-1B locally (greedy decoding so results are repeatable)."""
    global _pipe
    if _pipe is None:
        import torch
        from transformers import pipeline

        device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
        _pipe = pipeline("text-generation", model=MODEL_ID, device=device, dtype=torch.bfloat16)
    msgs = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    out = _pipe(msgs, max_new_tokens=768, do_sample=False)
    return out[0]["generated_text"][-1]["content"]


def _cached(generate: Generator, cache_dir: Optional[Path]) -> Generator:
    if cache_dir is None:
        return generate

    def run(prompt: str) -> str:
        f = cache_dir / (hashlib.sha256(prompt.encode()).hexdigest() + ".json")
        if f.is_file():
            return json.loads(f.read_text(encoding="utf-8"))
        res = generate(prompt)
        cache_dir.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(res), encoding="utf-8")
        return res

    return run


def _parse(output: str, chunk: List[Requirement]) -> Dict[str, List[str]]:
    """Turn 'KDE:/REQS:' blocks into {kde name: [titles]}, ignoring numbers not in the chunk."""
    if "ANSWER" in output:
        output = output.rsplit("ANSWER", 1)[1]
    titles = dict(chunk)
    groups: Dict[str, List[str]] = {}
    used = set()
    name = None
    for line in output.splitlines():
        line = line.strip().strip("*").strip()
        m = re.match(r"(?i)KDE\s*:\s*(.+)", line)
        if m:
            name = m.group(1).strip().strip("*").strip()
            continue
        m = re.match(r"(?i)REQS?\s*:\s*(.+)", line)
        if m and name:
            for num in re.findall(r"\d+(?:\.\d+)+", m.group(1)):
                if num in titles and num not in used:
                    used.add(num)
                    groups.setdefault(name, []).append(titles[num])
    for num, title in chunk:  # anything the model skipped still has to be in the output
        if num not in used:
            groups.setdefault(f"Section {num.split('.')[0]} other", []).append(title)
    return groups


def identify_kdes(
    documents: Dict[str, str],
    out_dir,
    generate: Optional[Generator] = None,
    yaml_prompt: str = "few-shot",
    cache_dir=None,
) -> Tuple[List[Path], List[dict]]:
    """Function 5: run every prompt type through Gemma and save one KDE YAML per document.

    The YAML file uses the output of `yaml_prompt`; all outputs are returned as records
    for dump_llm_outputs.
    """
    if yaml_prompt not in PROMPT_TYPES:
        raise ValueError(f"yaml_prompt must be one of {PROMPT_TYPES}")
    gen = _cached(generate or gemma_generate, Path(cache_dir) if cache_dir else None)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths, records = [], []
    for doc_name, text in documents.items():
        reqs = _requirements(text)
        if not reqs:
            raise ValueError(f"{doc_name}: no CIS recommendations found")
        merged: Dict[str, List[str]] = {}
        for chunk in _chunks(reqs):
            for ptype in PROMPT_TYPES:
                prompt = PROMPT_BUILDERS[ptype](_numbered(chunk))
                output = gen(prompt)
                records.append({"document": doc_name, "prompt_type": ptype, "prompt": prompt, "output": output})
                if ptype == yaml_prompt:
                    for name, titles in _parse(output, chunk).items():
                        merged.setdefault(name, []).extend(titles)
        kdes = {f"element{i}": {"name": n, "requirements": r} for i, (n, r) in enumerate(merged.items(), 1)}
        path = out_dir / f"{doc_name}-kdes.yaml"
        path.write_text(yaml.safe_dump(kdes, sort_keys=False, allow_unicode=True), encoding="utf-8")
        paths.append(path)
    return paths, records


def dump_llm_outputs(records: List[dict], out_path, llm_name: str = LLM_NAME) -> Path:
    """Function 6: write every prompt and LLM output to one TEXT file."""
    blocks = [
        f"*LLM Name*\n{llm_name}\n*Prompt Used*\n{r['prompt']}\n*Prompt Type*\n{r['prompt_type']}\n*LLM Output*\n{r['output']}\n"
        for r in records
    ]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(blocks), encoding="utf-8")
    return out_path
