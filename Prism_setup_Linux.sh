#!/bin/bash

parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd "$parent_path"

./Prism/Linux_Setup_Integrations.sh
./Prism/Linux_Setup_Startmenu.sh
