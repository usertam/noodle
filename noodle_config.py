#!/usr/bin/env python3

import os, os.path
import sys
from getpass import getpass
from base64 import b64encode

import requests
import jsonpickle
from lxml import html

# cd to the dir the script is located
abspath = os.path.abspath(sys.argv[0])
os.chdir(os.path.dirname(abspath))

print("============================")
print("[*] Noodle: Automated setup.")
print("============================")

# initialize new session
sess = requests.session()

# get login token from site
try:
    login_url = 'https://moodle.uowplatform.edu.au/login/index.php'
    page = sess.get(login_url)
    tree = html.fromstring(page.content)
    token = tree.xpath('//input[@name="logintoken"]/@value')[0]
except:
    print("[-] Unable to reach Moodle.")
    sys.exit(0)

print()
print("[*] This will require your login credentials.")
key = [ input('Username: '), getpass() ]
print()

# authenticate with payload; and
# halt if no proper credentials provided
try:
    payload = {
        'logintoken': token,
        'username': key[0],
        'password': key[1]
    }
except:
    print("[-] Invaild credentials.")
    sys.exit(0)

print("[*] Authenticating with Moodle.")
sess.post(login_url, data=payload)

# check login status by extracting username
try:
    page = sess.get('https://moodle.uowplatform.edu.au/my/')
    tree = html.fromstring(page.content)
    user = tree.xpath('//span[@class="usertext mr-1"]/text()')[0].title()
except:
    print("[-] Unable to login.")
    sys.exit(0)

print(f"[+] Hey there, {user}!")
print()
print("[*] Noodle will now analyze the sites. Hang tight!")

sites = []
for course_tree in tree.xpath('//div[@id="courses"]//div[contains(@id, "course-")]'):
    # ignore non subject sites
    if course_tree.xpath('.//small/text()')[0] != 'Subject':
        continue

    # extract site link
    href = str(course_tree.xpath('.//strong/a/@href')[0])

    # form html tree from site
    site_page = sess.get(href)
    site_tree = html.fromstring(site_page.content)

    # extract site title and code
    header = site_tree.xpath('./body/div/div/div/header')[0]
    title = header.xpath('.//h1/text()')[0].split(' ', 1)[1].strip()
    code = header.xpath('.//a[@aria-current="page"]/text()')[0].strip()

    # append site
    print(f'[+] Found: {title}')
    site = {
        'name': code,
        'href': href
    }
    sites.append(site)

print()
print("[*] Generating config.")

conf = {
    'login': b64encode(f'{key.pop(0)}:{key.pop(0)}'.encode('ascii')).decode("ascii")
    'sites': sites
}
with open('config.json', 'w') as f:
    f.write(jsonpickle.encode(conf, indent=4))

print('[*] Done!')
