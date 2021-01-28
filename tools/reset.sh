#!/bin/bash
set -e

# cd to project root
cd "$(dirname $0)/../"

# delete fetch list and files
rm -f fetch.txt downloads/*

# delete generated commit mail
rm -f mail/body.html
