#!/bin/bash
set -e

# cd to project root
cd "$(dirname $0)"

# initialize git if nessesary
if [ ! -d records/.git ]; then
    mkdir -p records
    git -C records init
fi

# fetch the latest sites via python script
python3 fetch_sites.py

# report and exit if no changes
if [ ! "$(git -C records ls-files -mo)" ]; then
    echo "[*] Already up-to-date. "
    exit 0
else
    echo "[*] Changes found. Writing commit. "
fi

# commit modified and new files
FILES=$(git -C records ls-files -mo | paste -s -d\ )
git -C records add $FILES
git -C records commit -m "update $FILES"

# launch "git show"
echo "[*] Showing full commit. "
sleep 3
git -C records show

# generate fetch list
echo "[*] Writing updated URLs to fetch list. "
git -C records show | \
    sed -n '/^+[^+]/ s/^+//p' | \
    tr -s ' ' | cut -d\  -f3 | \
    grep 'https' | grep 'resource\|assign' > fetch.txt || true

# fetch files if nessesary
if [ -s fetch.txt ]; then
    echo "[*] Fetching new files. "
    mkdir -p downloads
    python3 fetch_files.py
else
    echo "[*] Nothing to fetch. "
fi
