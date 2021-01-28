#!/usr/bin/env python3

from base64 import b64decode
from lxml import html
import os.path
import requests

def login_sess():
    # create session
    sess = requests.session()

    # get login token
    login_url = 'https://moodle.uowplatform.edu.au/login/index.php'
    page = sess.get(login_url)
    tree = html.fromstring(page.content)
    token = tree.xpath('//input[@name="logintoken"]/@value')[0]

    # get secret
    f = open("data/secret", "r").read()
    key = b64decode(f).decode("utf-8").rstrip().split(':', 1)

    # craft login payload
    payload = {
        'logintoken': token,
        'username': key[0],
        'password': key[1]
    }

    # send payload and return login session
    sess.post(login_url, data=payload)
    return sess

def fetch_url(session, url, dir):
    # get all herfs in page
    page = session.get(url)
    tree = html.fromstring(page.content)
    href_all = tree.xpath('.//section[@id="region-main"]//a/@href')

    # determine the right file href
    for href in href_all:
        if 'pluginfile.php' in href:
            name = os.path.basename(href).split("?")[0]
            break

    # print name, abort if unable to do so
    try:
        print("[+] Get: %s" % name)
    except:
        print("[-] Unable to find links on the URL.")
        return

    # download file
    r = session.get(href)
    with open(os.path.join(dir, name), "wb") as f:
        f.write(r.content)

# create login session
session = login_sess()

# read from file and download each url
with open("data/files.txt", "r") as f:
    for url in f:
        fetch_url(session, url, "files")
    
print("[+] Fetching files done!")
