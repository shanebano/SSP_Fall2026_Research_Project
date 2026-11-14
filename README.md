# SSP_Fall2026_Research_Project

Detects changes between two versions of the CIS Docker Benchmark and runs Hadolint on a set of Dockerfiles based on what changed.

## Team

| Name | BannerID | Email | Tasks |
|------|----------|-------|-------|
| Shane Banachowski | TBD | shb0064@auburn.edu | 2, 4 |
| Joseph Wilkerson | TBD | Jaw0216@auburn.edu | 1 |
| Rett Wilson | TBD | Jew0063@auburn.edu | 3 |

**LLM used for Task-1:** Gemma-3-1B (`google/gemma-3-1b-it`)

## Setup

```bash
python3 -m venv comp5700-venv
source comp5700-venv/bin/activate
pip install -r requirements.txt
hf auth login   # Gemma is gated: accept its license on Hugging Face first
```

`hadolint-bin` in `requirements.txt` installs the Hadolint executable into the venv.

## Running

```bash
python main.py docker-cis-v0.pdf docker-cis-v1.pdf --dockerfiles path/to/unzipped/dockerfiles
```

Results go to `output/<pdf1>_vs_<pdf2>/`:

| File | Task |
|------|------|
| `<pdf>-kdes.yaml` (one per PDF) | 1 |
| `llm_outputs.txt` | 1 |
| `element_names_diff.txt` | 2 |
| `element_requirements_diff.txt` | 2 |
| `hadolint_rules.txt` | 3 |
| `hadolint_results.csv` | 3 |

Options: `--out` sets the output folder, `--prompt` picks which prompt type's answers become the YAML (`zero-shot`, `few-shot` (default) or `chain-of-thought`), `--hadolint` points at a different Hadolint executable. Gemma answers are cached in `output/.cache/`, so a rerun is quick.

## Binary

```bash
./build.sh
./dist/cisdiff/cisdiff docker-cis-v0.pdf docker-cis-v1.pdf --dockerfiles path/to/dockerfiles
```

The binary takes the same arguments as `main.py`. Run it from the activated venv so Hadolint is on the PATH.

## How it works

**Task-1, Extractor (`cisdiff/extractor.py`)**
- `load_documents`: checks both inputs are real, readable PDFs and returns their text.
- `build_zero_shot_prompt`, `build_few_shot_prompt`, `build_chain_of_thought_prompt`: build the three prompts in `PROMPT.md`.
- `identify_kdes`: pulls the numbered recommendations out of each PDF, sends them to Gemma 12 at a time with each prompt type, and saves `<pdf>-kdes.yaml`.
- `dump_llm_outputs`: writes every prompt and answer to a text file.

**Task-2, Comparator (`cisdiff/comparator.py`)**
- `load_yaml_pair`: loads and validates the two YAML files.
- `compare_element_names`: KDE names found in only one file, or `NO DIFFERENCES IN REGARDS TO ELEMENT NAMES`.
- `compare_element_requirements`: `NAME,REQU` lines found in only one file, or `NO DIFFERENCES IN REGARDS TO ELEMENT REQUIREMENTS`.

**Task-3, Executor (`cisdiff/executor.py`)**
- `load_text_pair`: reads the two Task-2 files.
- `map_differences_to_rules`: maps differences to Hadolint rules for the CIS Dockerfile section, or writes `NO DIFFERENCES FOUND` / `NO MAPPING FOUND`.
- `run_hadolint`: scans every Dockerfile in the folder and returns a pandas DataFrame. All rules run when nothing mapped, otherwise only the mapped rules are kept.
- `write_results_csv`: writes `FilePath`, `DefaultSeverity`, `RULEID`, `COUNT`.

**Task-4**: `requirements.txt`, this README, the GitHub Actions workflow in `.github/workflows/tests.yml` (runs every test on each push and pull request and uploads the log), and the PyInstaller binary.

## Tests

```bash
pytest
```

One test per function across all three tasks. Gemma is replaced by a fake generator in the tests, so they run without downloading the model.

## Committed results

`output/` holds the results for all five input pairs. The Dockerfile dataset is not in the repo, so these CSVs come from two small sample Dockerfiles. Rerun with `--dockerfiles` pointed at the unzipped `dockerfiles.zip` to get the real scan.
