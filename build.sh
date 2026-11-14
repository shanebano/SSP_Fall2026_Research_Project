#!/usr/bin/env bash
# Build the cisdiff binary with PyInstaller into dist/cisdiff/.
set -euo pipefail
cd "$(dirname "$0")"
pyinstaller --noconfirm --clean --name cisdiff \
  --collect-all transformers --collect-all tokenizers --collect-all safetensors \
  --copy-metadata torch --copy-metadata tqdm --copy-metadata regex \
  --copy-metadata packaging --copy-metadata filelock --copy-metadata numpy \
  --copy-metadata huggingface-hub --copy-metadata pyyaml \
  main.py
echo "Binary: dist/cisdiff/cisdiff"
