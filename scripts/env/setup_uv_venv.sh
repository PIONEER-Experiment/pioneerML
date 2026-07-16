#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_ROOT"

ENV_DIR=".venv"
ENV_PROMPT="pioneerml"
PYTHON_VERSION="3.13"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. Install via: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi

# Create the environment if missing, or rebuild it when its Python version differs.
if [ -x "$ENV_DIR/bin/python" ]; then
  CURRENT_PYTHON_VERSION="$("$ENV_DIR/bin/python" -c 'import platform; print(platform.python_version())')"
  if [[ "$CURRENT_PYTHON_VERSION" == "$PYTHON_VERSION" || "$CURRENT_PYTHON_VERSION" == "$PYTHON_VERSION".* ]]; then
    echo "Using existing $ENV_DIR (python=${CURRENT_PYTHON_VERSION})."
  else
    echo "Recreating $ENV_DIR: python ${CURRENT_PYTHON_VERSION} -> ${PYTHON_VERSION}"
    uv venv "$ENV_DIR" --clear --python "$PYTHON_VERSION" --prompt "$ENV_PROMPT"
  fi
else
  echo "Creating $ENV_DIR with prompt '$ENV_PROMPT' (python=${PYTHON_VERSION})..."
  uv venv "$ENV_DIR" --python "$PYTHON_VERSION" --prompt "$ENV_PROMPT"
fi

source "$ENV_DIR/bin/activate"

INSTALL_FILE="$REPO_ROOT/requirements.txt"
echo "Installing dependencies from $INSTALL_FILE using uv..."
uv pip install -r "$INSTALL_FILE"

# Install package in editable mode
uv pip install -e "$REPO_ROOT"

# Ensure ipykernel exists without relying on pip being installed in the uv venv.
uv pip install -U ipykernel >/dev/null

# Register Jupyter kernel automatically if not already present
if ! jupyter kernelspec list 2>/dev/null | grep -Eq "^[[:space:]]*${ENV_PROMPT}[[:space:]]"; then
  echo "Registering Jupyter kernel '$ENV_PROMPT'..."
  python -m ipykernel install --user \
    --name "${ENV_PROMPT}" \
    --display-name "Python (${ENV_PROMPT})"
else
  echo "Kernel '$ENV_PROMPT' already registered."
fi

echo "Done. Activate with: source $ENV_DIR/bin/activate"
