FROM registry.dp.tech/dptech/ubuntu:20.04-py3.10

LABEL maintainer="tianhanz" \
      description="OpenFOAM 9 + detonationFoam V2.0 (DLBFoam, improved flux schemes)"

ENV DEBIAN_FRONTEND=noninteractive

# --- System deps + OpenMPI ---
RUN apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends \
        software-properties-common wget gnupg2 \
        build-essential flex bison cmake git \
        openmpi-bin libopenmpi-dev \
        zlib1g-dev libreadline-dev && \
    rm -rf /var/lib/apt/lists/*

# --- OpenFOAM 9 from official APT ---
RUN wget -qO /etc/apt/trusted.gpg.d/openfoam.asc https://dl.openfoam.org/gpg.key && \
    add-apt-repository -y http://dl.openfoam.org/ubuntu && \
    apt-get update -qq && \
    apt-get install -y -qq openfoam9 && \
    rm -rf /var/lib/apt/lists/*

# Source OF9 in all shells
RUN echo "source /opt/openfoam9/etc/bashrc" >> /etc/bash.bashrc

# --- Copy & compile detonationFoam ---
COPY applications/ /opt/detonationFoam/applications/

SHELL ["/bin/bash", "-c"]

# Compile libraries (skip dynamicMesh2D/dynamicFvMesh2D — not yet ported to OF9,
# only needed for adaptive mesh refinement which current cases don't use)
RUN source /opt/openfoam9/etc/bashrc && \
    cd /opt/detonationFoam/applications/solvers/detonationFoam_V2.0/fluxSchemes_improved && wmake libso && \
    cd /opt/detonationFoam/applications/libraries/DLBFoam-1.0-1.0_OF8/src && wmake libso

# Compile solver
RUN source /opt/openfoam9/etc/bashrc && \
    cd /opt/detonationFoam/applications/solvers/detonationFoam_V2.0 && wmake

# Verify
RUN source /opt/openfoam9/etc/bashrc && which detonationFoam_V2.0 && \
    ls $FOAM_USER_LIBBIN/lib*.so

WORKDIR /home/input
