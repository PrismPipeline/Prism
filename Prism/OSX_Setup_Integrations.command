#!/bin/bash

parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

cd "$parent_path"

python "Scripts/OSX_Pre-Install.py"

echo ""
echo "The Prism installer needs root priviledges to install Prism on this computer."
echo "Please enter the password of your root account:"

sudo python "Scripts/PrismInstaller.py"
python "Scripts/OSX_Post-Install.py"
