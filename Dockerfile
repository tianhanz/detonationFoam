FROM registry.dp.tech/dptech/ubuntu:20.04-py3.10

LABEL maintainer="tianhanz" \
      description="OpenFOAM 9 + detonationFoam V2.0 (ported from OF8, with AMR + DLBFoam)"

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

SHELL ["/bin/bash", "-c"]

# --- Copy solver source ---
# All libraries live under applications/solvers/detonationFoam_V2.0/
COPY applications/solvers/detonationFoam_V2.0/ /opt/detonationFoam/solver/

# --- Compile libraries (order matters for dependencies) ---

# 1. fluxSchemes_improved (no user-lib deps)
RUN source /opt/openfoam9/etc/bashrc && \
    cd /opt/detonationFoam/solver/fluxSchemes_improved && wmake libso

# 2. dynamicMesh2D -> libdynamicMesh2D.so (no user-lib deps)
RUN source /opt/openfoam9/etc/bashrc && \
    cd /opt/detonationFoam/solver/dynamicMesh2D/dynamicMesh && wmake libso

# 3. dynamicFvMesh2D -> libdynamicFvMesh2D.so (depends on libdynamicMesh2D)
RUN source /opt/openfoam9/etc/bashrc && \
    cd /opt/detonationFoam/solver/dynamicMesh2D/dynamicFvMesh && wmake libso

# 4. DLBFoam -> libchemistryModel_DLB.so (no user-lib deps)
RUN source /opt/openfoam9/etc/bashrc && \
    cd /opt/detonationFoam/solver/DLBFoam-1.0-1.0_OF8/src/thermophysicalModels/chemistryModel && wmake libso

# --- Compile solver executable ---
RUN source /opt/openfoam9/etc/bashrc && \
    cd /opt/detonationFoam/solver && wmake

# --- Verify build ---
RUN source /opt/openfoam9/etc/bashrc && \
    echo "=== Executable ===" && which detonationFoam_V2.0 && \
    echo "=== Libraries ===" && ls -1 $FOAM_USER_LIBBIN/lib*.so

# --- Copy test cases ---
COPY cases/ /opt/detonationFoam/cases/

WORKDIR /home/input
