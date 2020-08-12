#!/bin/bash

parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

cd "$parent_path"

if ! command -v brew &> /dev/null
then
    echo "installing homebrew"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
fi

echo "installing OpenImageIO"
brew install --build-from-source ./Scripts/openimageio.rb

oiioPath=$(find '/usr/local/Cellar/openimageio/' -regex '.*/lib/python2.7/site-packages/OpenImageIO.so')
if [ -z "$oiioPath" ]
then
    echo "Couldn't find OpenImageIO in /usr/local/Cellar/"
else
    echo "OpenImageIO was built successfully"
    ln -s $oiioPath ./PythonLibs/Python27
    echo "Creating a symlink at ./PythonLibs/Python27"
fi
