#!/bin/bash
set -e

# cd to mail directory
cd "$(dirname $0)"

# write email content
git -C "../records" show --color=always | aha -s > body.html
sed -i 's+</style>+pre {font-size:12px;}\n</style>+' body.html

# make email
echo "[+] Email made! "
