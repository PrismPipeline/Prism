#!/bin/bash

parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

cd "$parent_path"

echo ""
echo "The Prism installer needs root priviledges to uninstall Prism from this computer."
echo "Please enter the password of your root account:"

sudo python "Scripts/PrismInstaller.py" uninstall
