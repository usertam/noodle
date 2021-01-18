#!/bin/bash
set -e

# go to mail directory
cd "$(dirname $0)/../mail/"

# prompt for header items
read -p "Subject: " SUBJECT
read -p "From: " FROM
read -p "To: " TO

# write header
cat <<EOF > header.txt
Subject: $SUBJECT
From: $FROM
To: $TO
EOF
