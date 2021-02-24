#!/usr/bin/env python3

from base64 import b64encode
import os, os.path, sys

abspath = os.path.abspath(sys.argv[0])
os.chdir(os.path.dirname(abspath))

print("=" * 48)
print("[*] Noodle - Secret writer")
print("[*] This will store your credentials in base64-encoded format.")
print("[*] Noodle needs this to authenticate with Moodle to function.")
print("=" * 48)

try:
    with open("secret", "wb") as f:
        u = input("Enter username: ")
        p = input("Enter password: ")
        key = "{0}:{1}".format(u, p)
        key = b64encode(key.encode('ascii'))
        f.write(key)
except:
    print("[-] Unable to write to secret.")
