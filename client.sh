#!/bin/bash

# Clear out any home directories, but keep the tar file
rm -rf ~/.gridtogo/opensim-0.7.3
rm -rf ~/.gridtogo/opensim
PYTHONPATH="/usr/local/lib64/python2.7/site-packages:." python2.7 bin/gridtogo $@
