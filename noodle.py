#!/usr/bin/env python3

from base64 import b64decode
from lxml import html
from datetime import datetime
import git
import os, os.path
import shutil
import requests
import sys

def login_creds():
    try:
        with open("data/secret", "r") as f:
            key = f.read()
        key = b64decode(key).decode('ascii').split(":", 1)
    except:
        print("[-] Unable to read secret.")
        print("[-] Try \"python data/secret.py\" to create one.")
        exit()
    return key

def login_sess():
    # initialize a session
    sess = requests.session()

    # prepare the key
    key = login_creds()

    # get login token
    try:
        login_url = "https://moodle.uowplatform.edu.au/login/index.php"
        page = sess.get(login_url)
        tree = html.fromstring(page.content)
        token = tree.xpath('//input[@name="logintoken"]/@value')[0]
    except:
        print("[-] Unable to reach Moodle.")
        exit()

    # craft login payload
    payload = {
        "logintoken": token,
        "username": key[0],
        "password": key[1]
    }

    # authenticate
    sess.post(login_url, data=payload)

    # test login status by extracting username
    try:
        page = sess.get("https://moodle.uowplatform.edu.au/my/")
        tree = html.fromstring(page.content)
        user = tree.xpath('//span[@class="usertext mr-1"]/text()')[0]
    except:
        print("[-] Unable to login. Check the password?")
        exit()

    return sess, user

def fetch_page(sess, url, txt):
    # fetch page using login session
    page = sess.get(url)
    tree = html.fromstring(page.content)

    # open file
    f = open(txt, "w")

    # write page title
    header = tree.xpath('./body/div/div/div/header')[0]
    title = header.xpath('.//h1/text()')[0]
    subtitle = header.xpath('.//a[@aria-current="page"]/text()')[0]
    f.write("# %s\n" % title)
    f.write("# %s\n" % subtitle)
    f.write("\n")

    # write sections (week 1, 2...)
    for section in tree.xpath('//li[@role="region"]/div[@class="content"]'):

        # write section title
        title = section.xpath('./h3//text()')[0]
        f.write("# %s\n" % title)

        # write section summary text if any in list
        for text in section.xpath('.//div[@class="summary"]//text()'): 
            f.write("- %s\n" % text)

        # write resources (lecture notes, assignments...)
        for module in section.xpath('./ul/li'):

            for res in module.xpath('.//div[@class="activityinstance"]'):

                if len(module.xpath('.//a[@class="aalink"]')) > 0:
                    # resource is a link
                    res = module.xpath('.//a[@class="aalink"]')[0]

                # write resource name, and type if any
                desc = res.xpath('.//text()')
                f.write(" " * 2 + "* %s" % desc[0])
                if len(desc) > 1:
                    f.write(" [%s]" % desc[1].strip())

                # write restricted tag if resource is dimmed
                if len(module.xpath('.//div[contains(@class,"dimmed")]')) > 0:
                    f.write(" [Restricted]")

                # done tags, write newline
                f.write("\n")

                # write href if any
                for href in res.xpath('./@href'):
                    f.write(" " * 4 + "- %s\n" % href)

            for res in module.xpath('.//div[@class="contentafterlink"]'):

                for text in res.xpath('.//div/text()'):
                    f.write(" " * 2 + "- %s\n" % text)

                for text in res.xpath('.//p//text()'):
                    f.write(" " * 2 + "- %s\n" % text)

                # zoom recording links
                for text in res.xpath('.//ul/li//text()'):
                    f.write(" " * 4 + "| %s\n" % text)

        # write newline
        f.write("\n")

    # close file
    f.close()

def fetch_file(sess, url, dir):
    # get all herfs in page
    page = sess.get(url)
    tree = html.fromstring(page.content)

    href = []
    for h in tree.xpath('//section[@id="region-main"]/div[@role="main"]//a/@href'):
        if 'pluginfile.php' in h:
            href.append(h.split("?")[0])

    for h in href:
        name = os.path.basename(h)
        print("[+] Get: %s" % name)
        r = sess.get(h)
        with open(os.path.join(dir, name), "wb") as f:
            f.write(r.content)

abspath = os.path.abspath(sys.argv[0])
os.chdir(os.path.dirname(abspath))

print("=" * 48)
print("[*] Noodle: Automated web scraper for Moodle.")
print("[*] Started on: %s" % datetime.now().strftime("%c"))
print("=" * 48)

print("[*] Authenticating with Moodle.")

# create login session
sess, user = login_sess()
print("[+] Greetings, %s! <3" % user)

print("[*] Fetching course sites.")

# import site entries to fetch list
fetch = []
with open("data/sites.conf", "r") as f:
    for line in f:
        if line[0] == "-":
            s = [ line.strip("- \n"), next(f).rstrip() ]
            fetch.append(s)

if not fetch:
    print("[-] Nothing in fetch list!")
    print("[-] Configure sites to fetch in data/sites.conf.")
    exit()

if not os.path.exists("sites"):
    os.makedirs("sites")

for s in fetch:
    print("[*] %d/%d: %s" % (fetch.index(s)+1, len(fetch), s[0]) + " " * 8, end="\r")
    fetch_page(sess, s[1], os.path.join("sites", s[0]))

print("[+] %d sites fetched." % len(fetch) + " " * 8)

# initialize the repo objects
if not os.path.exists("sites/.git"):
    repo = git.Repo.init("sites")
    print("[*] First time using Noodle, I see!")
    print("[*] Noodle will need to initialize the site data first.")
    print("[*] Only future site changes from now will be tracked.")
    init = True
else:
    repo = git.Repo("sites")
    init = False
index = repo.index

# get changed files: modified and untracked
modified_files = [ item.a_path for item in index.diff(None) ]
files = modified_files + repo.untracked_files

# if nothing is changed then exit
if not files:
    print("[*] Already up-to-date!")
    exit()

if not init:
    print("[*] Site changes found! Writing commit.")

# make commit
index.add(files)
index.commit(" ".join(files))

if init:
    print("[+] Initialization completed!")
    exit()

print("=" * 48)
print("[+] Commit preview:")
print(repo.git.show("-U0", "--color=always"))
print("=" * 48)
print("[*] Tip: Try \"git -C sites show\" to see more context.")

if not os.path.exists("files"):
    os.makedirs("files")

fetch = []
for line in repo.git.diff("HEAD~1").split("\n"):
    if line[0] == "+" and "+++" not in line:
        if "https:" in line and ("resource" in line or "assign" in line):
            fetch.append(line.split("-")[1].strip(" "))

# if nothing in fetch list then exit
if not fetch:
    print("[*] No new files to fetch.")
    exit()

print("[*] Cleaning up directory.")

(_, _, leftovers) = next(os.walk("files"))
if leftovers and not os.path.exists(os.path.join("files", "archive")):
    os.makedirs(os.path.join("files", "archive"))

# move previously fetched files to archive
for f in leftovers:
    shutil.move(os.path.join("files", f), os.path.join("files", "archive", f))

print("[*] Fetching new files.")

# fetch file URLs in fetch list
for url in fetch:
    fetch_file(sess, url, "files")

print("[+] Fetching files done!")
