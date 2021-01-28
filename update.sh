#!/bin/bash
set -e

# cd to project root
cd "$(dirname $0)"

# initialize git if necessary
if [ ! -d sites/.git ]; then
    mkdir -p sites
    git -C sites init
fi

# fetch the latest sites via python script
echo "[*] Fetching latest sites. "
python3 fetch_sites.py

# report and exit if no changes
if [ ! "$(git -C sites ls-files -mo)" ]; then
    echo "[*] Already up-to-date. "
    exit 0
else
    echo "[*] Changes found. Writing commit. "
fi

# commit modified and new files
FILES=$(git -C sites ls-files -mo | paste -s -d\ )
git -C sites add $FILES
git -C sites commit -m "update $FILES"

# generate fetch list
echo "[*] Writing updated URLs to fetch list. "
git -C sites show -U0 | \
    cut -d- -f2 | cut -d\  -f2 | \
    grep 'https:' | grep 'resource\|assign' > data/files.txt || true

# fetch files if necessary
if [ -s data/files.txt ]; then
    echo "[*] Fetching new files. "
    rm -f files/*
    python3 fetch_files.py
else
    echo "[*] Nothing to fetch. "
    rm -f data/files.txt
fi

# go to mail directory
cd mail/

# make email
echo "[*] Making email. "
bash make.sh

# send email via python script
echo "[*] Sending email. "
python3 send.py
