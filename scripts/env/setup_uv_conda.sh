#!/usr/bin/env bash
set -euo pipefail

# This script bootstraps a minimal conda env with Python, installs uv,
# and uses uv to install project dependencies from requirements.txt.
#
# Usage:
#   ./scripts/env/setup_uv_conda.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

ENV_NAME="pioneerml"
REQ_FILE="requirements.txt"
PYTHON_VERSION="3.13"

if ! command -v conda >/dev/null 2>&1; then
  echo "conda is not available on PATH. Please install Miniconda/Anaconda first." >&2
  exit 1
fi

if conda env list | grep -q "^${ENV_NAME}[[:space:]]"; then
  CURRENT_PYTHON_VERSION="$(conda run -n "${ENV_NAME}" python -c 'import platform; print(platform.python_version())')"
  if [[ "${CURRENT_PYTHON_VERSION}" == "${PYTHON_VERSION}" || "${CURRENT_PYTHON_VERSION}" == "${PYTHON_VERSION}".* ]]; then
    echo "Using existing conda env: ${ENV_NAME} (python=${CURRENT_PYTHON_VERSION})"
  else
    echo "Updating conda env ${ENV_NAME}: python ${CURRENT_PYTHON_VERSION} -> ${PYTHON_VERSION}"
    UPDATE_SPECS=("python=${PYTHON_VERSION}")
    if conda list -n "${ENV_NAME}" '^root$' | grep -q '^root[[:space:]]'; then
      echo "ROOT is installed; upgrading it alongside Python to preserve ABI compatibility."
      UPDATE_SPECS+=("root")
    fi
    conda install -y -n "${ENV_NAME}" --override-channels -c conda-forge "${UPDATE_SPECS[@]}"
  fi
else
  echo "Creating conda env: ${ENV_NAME} (python=${PYTHON_VERSION})"
  conda create -y -n "${ENV_NAME}" --override-channels -c conda-forge "python=${PYTHON_VERSION}"
fi

echo "Activating env..."
eval "$(conda shell.bash hook)"
conda activate "${ENV_NAME}"

echo "Installing uv inside env..."
python -m pip install -U uv

# Keep large CUDA dependency installs from exhausting memory. These defaults can
# be overridden by exporting the variables before running this script.
export UV_CONCURRENT_DOWNLOADS="${UV_CONCURRENT_DOWNLOADS:-1}"
export UV_CONCURRENT_BUILDS="${UV_CONCURRENT_BUILDS:-1}"
export UV_CONCURRENT_INSTALLS="${UV_CONCURRENT_INSTALLS:-1}"

# uvloop is pulled in by ZenML's server extras. Invalidate only its cached
# artifacts to recover from partial/corrupted wheel downloads without throwing
# away the much larger cached CUDA/PyTorch wheels.
uv cache clean uvloop
if ! uv pip install --refresh-package uvloop "uvloop==0.22.1"; then
  echo "uv could not install uvloop; retrying that package with pip and no cache."
  python -m pip install --no-cache-dir "uvloop==0.22.1"
fi

echo "Installing dependencies from ${REQ_FILE} using uv..."
uv pip install -r "${REQ_FILE}"

# Install package in editable mode for clean imports (pioneerml importable without PYTHONPATH hacks)
uv pip install -e .

# Register kernel for notebooks
echo "Registering Jupyter kernel 'pioneerml' for this env..."
python -m ipykernel install --user --name "${ENV_NAME}" --display-name "Python (${ENV_NAME})" >/dev/null 2>&1 || true

echo "Done. Activate with: conda activate ${ENV_NAME}"
