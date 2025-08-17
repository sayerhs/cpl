#!/bin/bash

###
### Create a Conda package for Caelus Python Library
###

set -e

# Run from the script directory
cd ${0%/*} || exit 1

caelus_version="v5.0.0"
script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Set up conda environment
CONDA_ROOT=${CONDA_PREFIX:-${HOME}/anaconda/bin}
source ${CONDA_ROOT}/etc/profile.d/conda.sh

ostype=$(uname)
if [ "$ostype" = "Darwin" ]; then
    arch_type="osx-64"
else
    arch_type="linux-64"
fi

# Activate base/root environment for build and constructor
conda activate

if [ ! -d channels/${arch_type} ]; then
    mkdir -p channels/${arch_type}
fi

# Build the CPL package suitable for bundling with conda installer
conda build --output-folder ./channels caelus

# Convert to other platforms
pushd channels
conda convert -p osx-64 -p linux-64 ./$arch_type/caelus-${caelus_version}-py37_0.tar.bz2
popd

# Create the installer that bundles CPL and its dependencies
pushd installer
sed -e "s#LOCAL_CHANNEL_PATH#${script_dir}/channels#" construct-template.yaml > construct.yaml
constructor --platform=osx-64 .
constructor --platform=linux-64 .
du -h caelus*.sh
popd
