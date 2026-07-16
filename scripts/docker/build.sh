#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="pioneerml"
VERSION=""
BUILD_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--tag)
      IMAGE_NAME="$2"
      shift 2
      ;;
    -v|--version)
      VERSION="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: build.sh [-t|--tag name] [-v|--version version] [--no-cache]"
      exit 0
      ;;
    --no-cache)
      BUILD_ARGS+=(--no-cache)
      shift
      ;;
    *)
      echo "[build.sh] Unknown option: $1"
      exit 1
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -z "${VERSION}" ]]; then
  VERSION="$(awk -F'\"' '/^version[[:space:]]*=/ {print $2; exit}' "${ROOT_DIR}/pyproject.toml")"
  if [[ -z "${VERSION}" ]]; then
    VERSION="0.0.0"
  fi
fi

echo "[build.sh] Building ${IMAGE_NAME} (PIONEERML_VERSION=${VERSION}, Python 3.13) from ${ROOT_DIR}"
docker build \
  "${BUILD_ARGS[@]}" \
  -t "${IMAGE_NAME}" \
  --build-arg "PIONEERML_VERSION=${VERSION}" \
  "${ROOT_DIR}"
