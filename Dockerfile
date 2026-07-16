# CUDA-enabled PyTorch wheels provide the user-space CUDA runtime. GPU access is
# supplied at runtime by the host NVIDIA driver and NVIDIA Container Toolkit.
FROM ubuntu:22.04

ARG PIONEERML_VERSION=dev
ENV PIONEERML_VERSION=${PIONEERML_VERSION}

ENV DEBIAN_FRONTEND=noninteractive

# PyArrow, PyTorch, and PyTorch Geometric are installed from prebuilt wheels, so
# the image does not need CUDA, Arrow, or C++ development packages.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    nano \
    rsync \
    wget \
    && rm -rf /var/lib/apt/lists/*

ENV CONDA_DIR=/opt/conda
RUN curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-py313_26.5.3-1-Linux-x86_64.sh -o /tmp/miniconda.sh \
    && bash /tmp/miniconda.sh -b -p "${CONDA_DIR}" \
    && rm /tmp/miniconda.sh

ENV PATH="${CONDA_DIR}/bin:${PATH}"
SHELL ["bash", "-lc"]

WORKDIR /workspace

COPY requirements.txt requirements.txt
COPY pyproject.toml pyproject.toml
COPY README.md README.md
COPY src src
COPY scripts scripts

ENV PIP_INDEX_URL="https://download.pytorch.org/whl/cu126"
ENV PIP_EXTRA_INDEX_URL="https://pypi.org/simple"
ENV UV_PIP_INDEX_URL="https://download.pytorch.org/whl/cu126"
ENV UV_PIP_EXTRA_INDEX_URL="https://pypi.org/simple"
ENV PYTHON_VERSION=3.13

# Install Conda-managed binary packages before uv installs Python dependencies.
# This prevents a later ROOT solve from replacing uv-installed packages.
RUN conda create -y -n pioneerml --override-channels -c conda-forge "python=${PYTHON_VERSION}" root \
    && conda clean -afy

RUN ./scripts/env/setup_uv_conda.sh

COPY plugins plugins

# Initialize ZenML repository for the workspace.
RUN conda run -n pioneerml bash -lc "zenml init"

ENV CONDA_DEFAULT_ENV=pioneerml
ENV PATH="/opt/conda/envs/pioneerml/bin:${PATH}"
# Prefer the Conda environment's C++ runtime for PyROOT/cppyy. PyTorch's wheel
# dependencies provide their CUDA user-space libraries inside the environment.
ENV LD_LIBRARY_PATH="/opt/conda/envs/pioneerml/lib"
ENTRYPOINT ["bash", "-lc"]
CMD ["bash"]

# Set a consistent prompt with version info.
ENV PS1="\\[\\e[96m\\]pioneerml_v${PIONEERML_VERSION}@\\h\\[\\e[0m\\]:\\[\\e[93m\\]\\w\\[\\e[0m\\]\\$ "
RUN printf 'export PS1="\\[\\e[96m\\]pioneerml_v${PIONEERML_VERSION}@\\h\\[\\e[0m\\]:\\[\\e[93m\\]\\w\\[\\e[0m\\]\\$ "\n' \
    > /etc/profile.d/pioneerml_prompt.sh \
    && printf 'export PS1="\\[\\e[96m\\]pioneerml_v${PIONEERML_VERSION}@\\h\\[\\e[0m\\]:\\[\\e[93m\\]\\w\\[\\e[0m\\]\\$ "\n' \
    >> /root/.bashrc
