# PIONEER ML

PIONEER ML is the framework layer for model training and inference. The core
framework lives in `src/pioneerml`; model-specific code lives in plugins under
`plugins/`.

Default plugins:

- `plugins/PURITY`: current PURITY ATAR+LYSO model stack.
- `plugins/example_plugin`: tutorial and example components for learning the
  plugin API.

Legacy split-model code has been moved out of the default plugin set. It can be
kept separately as an optional plugin if someone needs those older workflows.

## Setup

Clone with submodules:

```bash
git clone --recurse-submodules https://github.com/jaca230/pioneerML.git
cd pioneerML
```

Docker is the recommended environment for PIONEER integration. Local setup is
also available:

```bash
./scripts/env/setup_uv_conda.sh
conda activate pioneerml
```

For manual plugin development, include the framework and plugin `src`
directories on `PYTHONPATH`:

```bash
export PYTHONPATH="$PWD/src:$PWD/plugins/PURITY/src:$PWD/plugins/example_plugin/src:$PYTHONPATH"
```
