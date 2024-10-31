#!/bin/bash

subfile=$1
file -bI $subfile | grep application/pdf >$subfile.errlog
retVal=$?
if [ $retVal -ne 0 ];
then
    exit 255
else
    exit 0
fi
