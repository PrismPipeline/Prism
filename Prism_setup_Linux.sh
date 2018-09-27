#!/bin/bash

parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

cd "$parent_path"

python "Prism/Pre-Install_Linux.py"

export LD_LIBRARY_PATH=./Prism/PrismFiles/PythonLibs/lib

python "Prism/InstallPrism.py"
