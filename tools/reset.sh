#!/bin/bash
set -e

# cd to project root
cd "$(dirname $0)"

# delete fetch list and files
rm -rf downloads fetch.txt mail/body.html
mkdir -p downloads

# delete records also if specified
if [ "$1" = "records" ]; then
    rm -rf records
fi
