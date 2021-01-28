#!/bin/bash
set -e

# cd to data
cd "$(dirname $0)/../data/"

# prompt for username and password
read -p "Username: " USER
read -s -p "Password: " PASS

# write secret
echo "$USER:$PASS" | base64 > secret
