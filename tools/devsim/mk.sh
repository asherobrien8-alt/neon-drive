#!/bin/sh
# mk.sh NAME : NAME.txt = pre_rebuild.txt + body_NAME.txt
cat pre_rebuild.txt scenarios/body_$1.txt > $1.txt
