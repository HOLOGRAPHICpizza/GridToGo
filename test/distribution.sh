#!/bin/bash

rm -rf ~/.gridtogo
PYTHONPATH="/usr/local/lib64/python2.7/site-packages:." python2.7 gridtogo/client/opensim/distribution.py
