#!/bin/bash
set -e

# set project root
PROJECT="$(dirname $0)"

# fetch the latest sites via python script
cd $PROJECT
python3 fetch_sites.py

# report and exit if no changes
if [ ! "$(git -C records ls-files -mo)" ]; then
    echo "[*] Already up-to-date. "
    exit 0
fi

echo "[*] Changes found. Writing commit. "

# commit modified and new files
FILES=$(git -C records ls-files -mo | paste -s -d\ )
git -C records add $FILES
git -C records commit -m "update $FILES"

# launch "git show"
echo "[*] Showing full commit. "
sleep 3
git -C records show

# ask user whether to fetch the new files or not
read -p "[?] Fetch updated files? [y/N] " CONT
[ "$(echo $CONT | tr '[A-Z]' '[a-z]')" = "y" ] || exit 0

# generate fetch list
echo "[*] Writing updated URLs to fetch list. "
git -C records show | \
    sed -n '/^+[^+]/ s/^+//p' | \
    tr -s ' ' | cut -d\  -f3 | \
    grep 'https' | grep 'resource\|assign' > fetch.txt || true

# terminate if nothing in fetch list
if [ ! -s fetch.txt ]; then
    echo "[*] Nothing to fetch. "
    exit 0
fi

# make sure the hardcoded directory exists
mkdir -p downloads

# fetch files via python script
echo "[*] Fetching new files. "
python3 fetch_files.py
