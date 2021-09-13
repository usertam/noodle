#!/usr/bin/env python3

import json
import os, os.path
import sys
from datetime import datetime
from urllib.parse import unquote
from base64 import b64decode

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
        desc = desc_tree[0].xpath('.//div/text() | .//p//text() | .//ul/li//text()') if len(desc_tree) > 0 else None
        self.desc = ' '.join(desc[0].split()) if desc is not None else None

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
                if 'pluginfile.php' in link and 'submission' not in link:
                    files.append(link.split("?")[0])

        # convert files to be immutable
        self.files = tuple(files)

        # set folder sub files
        folder = []
        if 'Folder' in self.tags and self.href != '#':
            page = sess.get(self.href)
            tree = html.fromstring(page.content)
            for link in tree.xpath('//div[@class="filemanager"]//a/@href'):
                if 'pluginfile.php' in link:
                    folder.append(link.split("?")[0])

        # convert files to be immutable
        self.folder = tuple(folder)

    def __hash__(self) -> int:
        return hash((self.title, self.desc, self.tags, self.href, self.files, self.folder))

    def __eq__(self, other) -> bool:
        return hash(self) == hash(other)


class Section:
    def __init__(self, tree):
        # set section title
        self.title = tree.xpath('./h3//text()')[0].strip()

        # set description if any
        desc_tree = tree.xpath('.//div[@class="summary"]')[0]
        desc = desc_tree[0].xpath('.//div/text() | .//p//text() | .//ul/li//text()') if len(desc_tree) > 0 else None
        self.desc = ' '.join(desc[0].split()) if desc is not None and len(desc) > 0 else None

        # add modules
        modules = []
        for mod_tree in tree.xpath('./ul/li'):
            modules.append(Module(mod_tree))

        # convert modules to be immutable
        self.modules = tuple(modules)

    def __hash__(self) -> int:
        return hash((self.title, self.desc, self.modules))

    def __eq__(self, other) -> bool:
        return hash(self) == hash(other)


class Site:
    def __init__(self, tree):
        header = tree.xpath('./body/div/div/div/header')[0]
        self.title = header.xpath('.//h1/text()')[0].split(' ', 1)[1].strip()
        self.code = header.xpath('.//a[@aria-current="page"]/text()')[0].strip()
        sections = []
        for sec_tree in tree.xpath('//li[@role="region"]/div[@class="content"]'):
            sections.append(Section(sec_tree))
        self.sections = tuple(sections)

    def __hash__(self) -> int:
        return hash((self.title, self.code, self.sections))

    def __eq__(self, other) -> bool:
        return hash(self) == hash(other)

    def files(self) -> list:
        ret = []
        for section in self.sections:
            for module in section.modules:
                ret += module.files
                ret += module.folder
        return ret

    def write_markdown(self, file):
        with open(file, 'w') as f:
            # write site title and code
            f.write(f'# {self.title}\n')
            f.write(f'`{self.code}`\n')
            f.write('\n')

            # write custom css style
            f.write('<style>\nul > li > ul > li { font-size: 75%; }\n</style>\n')
            f.write('\n')

            for sec_code, section in enumerate(self.sections, start=1):
                # write section title
                f.write(f'## {section.title}\n')

                # write section summary if any
                if section.desc is not None:
                    f.write(f'> {section.desc}\n')
                    f.write('\n')

                # write module entires
                mod_code = 0
                for mod_code, module in enumerate(section.modules, start=1):
                    # write module title
                    f.write(f'- [{module.title}][s{sec_code}-{mod_code}]\n')

                    # write module files if any
                    file_code = 1
                    if len(module.files) > 0:
                        # module files header
                        f.write(' ' * 2 + '- DL: ')
                        for file_code, file in enumerate(module.files, start=1):
                            name = unquote(os.path.basename(file))
                            code = f's{sec_code}-{mod_code}-f{file_code}'
                            if file_code > 1: f.write(', ')
                            f.write(f'[{name}][{code}]')
                        # module files footer
                        f.write('\n')

                    # write module description if any
                    if module.desc is not None:
                        f.write(f'  - {module.desc}\n')

                    # write files inside folder
                    for file_code, file in enumerate(module.folder, start=file_code):
                        name = unquote(os.path.basename(file))
                        code = f's{sec_code}-{mod_code}-f{file_code}'
                        f.write(f'  - [{name}][{code}]\n')

                # write newline if no modules are written
                if mod_code > 0:
                    f.write('\n')

                # write module and files references
                for mod_code, module in enumerate(section.modules, start=1):
                    f.write(f'[s{sec_code}-{mod_code}]: {module.href} "{module.tags}"\n')
                    for file_code, file in enumerate(module.files + module.folder, start=1):
                        code = f's{sec_code}-{mod_code}-f{file_code}'
                        f.write(f'[{code}]: {file} "Direct Link"\n')

                # default padding
                f.write('\n')


def find_lcs(S1, S2):
    # populate the table
    m, n = len(S1), len(S2)
    table = [ [ 0 for x in range(n+1) ] for x in range(m+1) ]
    for i in range(1, m+1):
        for j in range(1, n+1):
            if S1[i-1] == S2[j-1]:
                table[i][j] = table[i-1][j-1] + 1
            else:
                table[i][j] = max(table[i-1][j], table[i][j-1])

    # find the lcs
    lcs = []
    index = table[m][n]
    while m > 0 and n > 0:
        if S1[m-1] == S2[n-1]:
            lcs.insert(0, S1[m-1])
            m -= 1
            n -= 1
            index -= 1
        elif table[m-1][n] > table[m][n-1]:
            m -= 1
        else:
            n -= 1

    return lcs


class DiffSec:
    def __init__(self, sec_a, sec_b):
        self.title = sec_b.title
        self.desc = sec_b.desc
        self.flag = 0
        lcs_mods = find_lcs(sec_a.modules, sec_b.modules)
        modules = []
        for i in range(max(len(sec_a.modules), len(sec_b.modules))):
            if i < len(sec_a.modules) and sec_a.modules[i] not in lcs_mods:
                module = sec_a.modules[i]
                module.flag = 1
                modules.append(module)
            if i < len(sec_b.modules) and sec_b.modules[i] not in lcs_mods:
                module = sec_b.modules[i]
                module.flag = 2
                modules.append(module)
        self.modules = modules


class Diff:
    def __init__(self, site, prev, time_a, time_b):
        # basic info
        self.title = site.title
        self.code = site.code

        # format commit times
        if time_a.strftime('%x') == time_b.strftime('%x'):
            self.time_b = time_b.strftime('%H:%M')
        else:
            self.time_b = time_b.strftime('%b %d %H:%M')
        self.time_a = time_a.strftime('%b %d %H:%M')

        # build longest common subsequence
        lcs_secs = find_lcs(site.sections, prev.sections)

        # generate whole section diffs
        sections = []
        for i in range(max(len(site.sections), len(prev.sections))):
            if i < len(prev.sections) and prev.sections[i] not in lcs_secs:
                section = prev.sections[i]
                section.flag = 1
                sections.append(section)
            if i < len(site.sections) and site.sections[i] not in lcs_secs:
                section = site.sections[i]
                section.flag = 2
                sections.append(section)

        # replace consecutive del/add diffs with precise section diffs
        i = 0
        while i < len(sections) - 1:
            if sections[i].flag == 1 and sections[i+1].flag == 2:
                if sections[i].title == sections[i+1].title:
                    section = DiffSec(sections[i], sections[i+1])
                    sections.pop(i)
                    sections.pop(i)
                    sections.insert(i, section)
            i += 1

        self.sections = sections

    def files(self) -> list:
        ret = []
        for section in self.sections:
            if section.flag != 1:
                for module in section.modules:
                    if not hasattr(module, 'flag') or module.flag != 1:
                        ret += module.files
                        ret += module.folder
        return ret

    def write_markdown(self, file):
        if len(self.sections) == 0: return
        with open(file, 'w') as f:
            # write site title and code
            f.write(f'# {self.title}\n')
            f.write(f'`{self.code}` ')
            f.write(f'`DIFF: {self.time_a} ➝ {self.time_b}`\n')
            f.write('\n')

            # write custom css style
            f.write('<style>\n')
            f.write('add { color: green; }\n')
            f.write('del { color: red; text-decoration: none; }\n')
            f.write('ul > li > ul > li { font-size: 75%; }\n')
            f.write('</style>\n')
            f.write('\n')

            for sec_code, section in enumerate(self.sections, start=1):
                # color output according to diff flags
                if section.flag == 1:
                    prefix, suffix = '<del>', '</del>'
                elif section.flag == 2:
                    prefix, suffix = '<add>', '</add>'
                else:
                    prefix, suffix = '', ''

                # write section title
                f.write(f'## {prefix}{section.title}{suffix}\n')

                # write section summary if any
                if section.desc is not None:
                    f.write(f'> {prefix}{section.desc}{suffix}\n')
                    f.write('\n')

                # write module entires
                mod_code = 0
                for mod_code, module in enumerate(section.modules, start=1):
                    # color output according to diff flags
                    if section.flag == 1:
                        prefix, suffix = '<del>', '</del>'
                    elif section.flag == 2:
                        prefix, suffix = '<add>', '</add>'
                    elif module.flag == 1:
                        prefix, suffix = '<del>', '</del>'
                    elif module.flag == 2:
                        prefix, suffix = '<add>', '</add>'
                    else:
                        prefix, suffix = '', ''

                    # write module title
                    f.write(f'- [{prefix}{module.title}{suffix}][s{sec_code}-{mod_code}]\n')

                    # write module files if any
                    file_code = 1
                    if len(module.files) > 0:
                        # module files header
                        f.write(' ' * 2 + '- DL: ')
                        for file_code, file in enumerate(module.files, start=1):
                            name = unquote(os.path.basename(file))
                            code = f's{sec_code}-{mod_code}-f{file_code}'
                            if file_code > 1: f.write(', ')
                            f.write(f'[{prefix}{name}{suffix}][{code}]')
                        # module files footer
                        f.write('\n')

                    # write module description if any
                    if module.desc is not None:
                        f.write(f'  - {prefix}{module.desc}{suffix}\n')

                    # write files inside folder
                    for file_code, file in enumerate(module.folder, start=file_code):
                        name = unquote(os.path.basename(file))
                        code = f's{sec_code}-{mod_code}-f{file_code}'
                        f.write(f'  - [{prefix}{name}{suffix}][{code}]\n')

                # write newline if no modules are written
                if mod_code > 0:
                    f.write('\n')

                # write module and files references
                for mod_code, module in enumerate(section.modules, start=1):
                    f.write(f'[s{sec_code}-{mod_code}]: {module.href} "{module.tags}"\n')
                    for file_code, file in enumerate(module.files + module.folder, start=1):
                        code = f's{sec_code}-{mod_code}-f{file_code}'
                        f.write(f'[{code}]: {file} "Direct Link"\n')

                # default padding
                f.write('\n')


def load_config(key):
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)[key]
    except:
        print("[-] Unable to read config.")
        sys.exit(0)
    return config


def login():
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

    # authenticate with payload; and
    # halt if no proper credentials provided
    try:
        key = b64decode(load_config('login')).decode().split(':', 1)
        payload = {
            'logintoken': token,
            'username': key.pop(0),
            'password': key.pop(0)
        }
    except:
        print("[-] Invaild credentials.")
        sys.exit(0)

    sess.post(login_url, data=payload)

    # check login status by extracting username
    try:
        page = sess.get('https://moodle.uowplatform.edu.au/my/')
        tree = html.fromstring(page.content)
        user = tree.xpath('//span[@class="usertext mr-1"]/text()')[0].title()
    except:
        print("[-] Unable to login.")
        sys.exit(0)

    return sess, user


# cd to the dir the script is located
abspath = os.path.abspath(sys.argv[0])
os.chdir(os.path.dirname(abspath))

print("=" * 48)
print("[*] Noodle: Automated web scraper for Moodle.")
print("[*] Started on:", datetime.now().strftime('%c'))
print("=" * 48)

# create login session
print("[*] Authenticating with Moodle.")
global sess, user
sess, user = login()
print(f"[+] Greetings, {user}! <3")

# import site entries to fetch
conf = load_config('sites')
if not conf:
    print("[-] Nothing in site entries!")
    print("[*] Configure sites to fetch in config.json.")
    sys.exit(0)
else:
    print("[*] Fetching course sites.")

# fetch and parse sites
sites = []
total = len(conf)

for index, site in enumerate(conf, start=1):
    # print progress
    status = f"[*] {index}/{total}: {site['name']}"
    print(status + ' ' * 4, end='\r')

    # parse site as html tree
    page = sess.get(site['href'])
    tree = html.fromstring(page.content)
    sites.append(Site(tree))

print(f"[+] {total} sites fetched." + ' ' * 12)

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
    name = site.code + '.json'
    data = jsonpickle.encode(site, indent=4)

    # create blob and write to tree
    blob = repo.create_blob(data)
    tree.insert(name, blob, pygit2.GIT_FILEMODE_BLOB)

# write tree and compare; create commit only if there are changes
tree_id = tree.write()
if prev is not None:
    tree_diff = repo.get(tree_id).diff_to_tree(prev.tree, 1)
else:
    empty = repo.get(repo.TreeBuilder().write())
    tree_diff = repo.get(tree_id).diff_to_tree(empty, 1)

if tree_diff and 'no_commit' not in sys.argv[1:]:
    # noodle default signature
    signature = pygit2.Signature('noodle', 'noodle@localhost')
    # create commit
    commit_id = repo.create_commit(
        head.name if head is not None else 'refs/heads/master',
        signature, signature,
        '',
        tree_id,
        [ head.target ] if head is not None else []
    )

# print git status
status = tree_diff.stats.format(2, 1)
print('[*] Git:' + status, end='')

# create markdown dir
if not os.path.exists('markdown'):
    os.mkdir('markdown')

# reserved for download function
dl_targets = []

# write site and diff markdowns
for site in sites:
    # write site data markdown
    file = os.path.join('markdown', site.code + '.md')
    site.write_markdown(file)

    # load the previous site, skip if none exists
    name = site.code + '.json'
    if prev is not None and name in prev.tree:
        # generate diff
        prev_site = jsonpickle.loads(prev.tree[name].data.decode())
        time_a = datetime.fromtimestamp(prev.commit_time).astimezone()
        time_b = datetime.now().astimezone()
        diff = Diff(site, prev_site, time_a, time_b)

        # write diff markdown
        file = os.path.join('markdown', site.code + '.diff.md')
        diff.write_markdown(file)

        # determine if there are materials to fetch
        if diff.files():
            dl_targets.append(diff)
    else:
        # since this is a new site, download all that exists
        dl_targets.append(site)

print("[*] Generating markdown index.")

with open(os.path.join('markdown', 'index.md'), 'w') as f:
    f.write('# Noodle\n\n')
    f.write('<style>\nul > li > ul > li { font-size: 80%; }\n</style>\n\n')
    f.write('## All sites\n\n')
    for site in sites:
        f.write(f"- [{site.title}]({site.code + '.md'})\n")
        try:
            with open(os.path.join('markdown', site.code + '.diff.md'), 'r') as diff:
                diff.readline()
                diff_delta = diff.readline().split('`')[3]
                f.write(f"  - [`{diff_delta}`]({site.code + '.diff.md'})\n")
        except:
            f.write(f"  - [`DIFF: None`]\n")

if not dl_targets:
    print("[*] Course materials are up-to-date.")
else:
    print("[*] Fetching new course materials.")

for diff in dl_targets:
    # download new files
    files = diff.files()
    total = len(files)

    for index, link in enumerate(files, start=1):
        # set file name and download location
        name = unquote(os.path.basename(link))
        dl_dir = os.path.join('download', diff.code)

        # print status
        status = f"[*] {diff.code}: {index}/{total}"
        print(status + ' ' * 4, end='\r')

        # create download dir
        if not os.path.exists(dl_dir):
            os.makedirs(dl_dir)
        
        # download
        file = os.path.join(dl_dir, name)
        r = sess.get(link)
        with open(file, "wb") as f:
            f.write(r.content)

    # print status
    status = f"[+] {diff.code}: {total} files fetched."
    print(status + ' ' * 4)
