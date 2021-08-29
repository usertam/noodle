#!/usr/bin/env python3

import datetime
import json
import os, os.path
import sys
from urllib.parse import unquote

import jsonpickle
import pygit2
import requests
from lxml import html

class Module:
    def __init__(self, tree):
        # set resource tree; shift to aalink subtree if it exists
        res_tree = tree.xpath('.//div[@class="activityinstance"]')[0]
        aalink = res_tree.xpath('.//a[@class="aalink"]')
        if aalink: res_tree = aalink[0]

        # set module title
        text = res_tree.xpath('.//text()')
        self.title = text.pop(0).strip()

        # set description if any
        desc_tree = tree.xpath('.//div[@class="contentafterlink"]')
        desc = desc_tree[0].xpath('.//div/text() | .//p//text() | .//ul/li//text()')[0] if len(desc_tree) > 0 else None
        self.desc = ' '.join(desc.split()) if desc is not None else None

        # set tags, aka the rest of the text()
        tags = [ t.strip() for t in text ]
        if res_tree.xpath('./div[contains(@class,"dimmed")]'):
            tags.append("Restricted")
        self.tags = ', '.join(tags)

        # set link to page
        href = res_tree.xpath('./@href')
        self.href = href[0].strip() if len(href) > 0 else '#'

        # set download-able files
        files = []
        if ('File' in self.tags or 'Assignment' in self.tags) and self.href != '#':
            page = sess.get(self.href)
            tree = html.fromstring(page.content)
            for link in tree.xpath('//section[@id="region-main"]/div[@role="main"]//a/@href'):
                if 'pluginfile.php' in link:
                    files.append(link.split("?")[0])
        
        # convert files to be immutable
        self.files = tuple(files)


class Section:
    def __init__(self, tree):
        # set section title
        self.title = tree.xpath('./h3//text()')[0].strip()

        # set description if any
        desc_tree = tree.xpath('.//div[@class="summary"]')[0]
        desc = desc_tree[0].xpath('.//div/text() | .//p//text() | .//ul/li//text()')[0] if len(desc_tree) > 0 else None
        self.desc = ' '.join(desc.split()) if desc is not None else None

        # add modules
        modules = []
        for mod_tree in tree.xpath('./ul/li'):
            modules.append(Module(mod_tree))

        # convert modules to be immutable
        self.modules = tuple(modules)


class Site:
    def __init__(self, tree):
        header = tree.xpath('./body/div/div/div/header')[0]
        self.title = header.xpath('.//h1/text()')[0].split(' ', 1)[1].strip()
        self.code = header.xpath('.//a[@aria-current="page"]/text()')[0].strip()
        sections = []
        for sec_tree in tree.xpath('//li[@role="region"]/div[@class="content"]'):
            sections.append(Section(sec_tree))
        self.sections = tuple(sections)

    def write_markdown(self, file):
        with open(file, 'w') as f:
            # write site title and code
            f.write(f'# {self.title}\n')
            f.write(f'`{self.code}`\n')
            f.write('\n')

            # write custom css style
            f.write('<style>\nfile { float: right; font-size: 70%; }\n</style>\n')
            f.write('\n')

            for sec_code, section in enumerate(self.sections, start=1):
                # write section title
                f.write(f'## {section.title}\n')

                # write section summary if any
                if section.desc is not None:
                    f.write(f'> <small>{section.desc}</small>\n')
                    f.write('\n')

                # write module entires
                for mod_code, module in enumerate(section.modules, start=1):
                    # write module title
                    f.write(f'- [{module.title}][s{sec_code}-{mod_code}]\n')

                    # write module files if any
                    if len(module.files) > 0:
                        # module files header
                        f.write(' ' * 4 + '<file>DL: ')
                        for file_code, file in enumerate(module.files, start=1):
                            name = unquote(os.path.basename(file))
                            code = f's{sec_code}-{mod_code}-f{file_code}'
                            if file_code > 1: f.write(', ')
                            f.write(f'[{name}][{code}]')
                        # module files footer
                        f.write('</file>\n')

                    # write module dscription if any
                    if module.desc is not None:
                        f.write(f'  - <small>{module.desc}</small>\n')

                # write newline if no modules are written
                if mod_code > 0:
                    f.write('\n')

                # write module and filesreferences
                for mod_code, module in enumerate(section.modules, start=1):
                    f.write(f'[s{sec_code}-{mod_code}]: {module.href} "{module.tags}"\n')
                    for file_code, file in enumerate(module.files, start=1):
                        code = f's{sec_code}-{mod_code}-f{file_code}'
                        f.write(f'[{code}]: {file} "Direct Link"\n')

                # default padding
                f.write('\n')  


def load_config():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except:
        print("[-] Unable to read config.")
        sys.exit(0)
    return config


def login(key):
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

    # authenticate with payload
    payload = {
        'logintoken': token,
        'username': key['user'],
        'password': key['pass']
    }
    sess.post(login_url, data=payload)

    # check login status by extracting username
    try:
        page = sess.get('https://moodle.uowplatform.edu.au/my/')
        tree = html.fromstring(page.content)
        user = tree.xpath('//span[@class="usertext mr-1"]/text()')[0]
    except:
        print("[-] Unable to login. Check the password?")
        sys.exit(0)

    return sess, user


# cd to the dir the script is located
abspath = os.path.abspath(sys.argv[0])
os.chdir(os.path.dirname(abspath))

# load config
conf = load_config()

print("=" * 48)
print("[*] Noodle: Automated web scraper for Moodle.")
print("[*] Started on:", datetime.datetime.now().strftime('%c'))
print("=" * 48)

# create login session
print("[*] Authenticating with Moodle.")
global sess, user
sess, user = login(conf['login'][0])

print(f"[+] Greetings, {user}! <3")
print("[*] Fetching course sites.")

# import site entries to fetch
sites = conf['sites']
if not sites:
    print("[-] Nothing in site entries!")
    print("[-] Configure sites to fetch in data/sites.conf.")
    sys.exit(0)

# variables for fetch progress
prog_now = 0
prog_max = len(sites)
padding = ' ' * 16

# fetch sites and create data objects
for site in sites:
    # print progress
    prog_now += 1
    status = f"[*] {prog_now}/{prog_max}: {site['name']}"
    print(status + padding, end='\r')

    # parse site as html tree
    page = sess.get(site['href'])
    tree = html.fromstring(page.content)

    # create object from tree and append data to object
    site['data'] = Site(tree)
    site['time'] = datetime.datetime.now()

print(f"[+] {prog_now} sites fetched." + padding)

# initialize git repo
if not os.path.exists('json/.git'):
    pygit2.init_repository('json', False)
repo = pygit2.Repository('json/.git')

# create working tree
try:
    head = repo.head
    prev = repo.get(head.target)
    tree = repo.TreeBuilder(prev.tree)
except:
    head = None
    prev = None
    tree = repo.TreeBuilder()

# write site data to working tree
for site in sites:
    # set site filename and contents
    name = site['data'].code + '.json'
    data = jsonpickle.encode(site['data'], indent=4)

    # create blob and write to tree
    blob = repo.create_blob(data)
    tree.insert(name, blob, pygit2.GIT_FILEMODE_BLOB)

# write tree and compare; create commit only if there are changes
tree_id = tree.write()
signature = pygit2.Signature('noodle', 'noodle@localhost')
if prev is None or repo.get(tree_id).diff_to_tree(prev.tree).__len__() != 0:
    # create commit
    commit_id = repo.create_commit(
        head.name if head is not None else 'refs/heads/master',
        signature, signature,
        '',
        tree_id,
        [ head.target ] if head is not None else []
    )

# create markdown dir
if not os.path.exists('markdown'):
    os.mkdir('markdown')

# write site and diff markdowns
for site in sites:
    # set site variables
    code = site['data'].code

    # write site data markdown
    file = os.path.join('markdown', code + '.md')
    site['data'].write_markdown(file)
