#!/bin/bash
set -e

# cd to project root
cd "$(dirname $0)/../"

# prompt for username and password
read -p "Username: " USER
read -s -p "Password: " PASS

# write secret
echo "$USER:$PASS" | base64 > secret
