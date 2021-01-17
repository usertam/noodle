#!/usr/bin/env python3

from base64 import b64decode
from lxml import html
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
    f = open("secret", "r").read()
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

def fetch_page(session, view_id, filename):
    # fetch page using login session
    page = session.get("https://moodle.uowplatform.edu.au/course/view.php?id=%s" % view_id)
    tree = html.fromstring(page.content)

    # open file
    f = open(filename, "w")

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

            if len(module.xpath('.//ul')) > 0:
                # not resource, just a module of text
                for text in module.xpath('.//ul/li//text()'):
                    f.write(" " * 4 + "| %s\n" % text)
                # proceed to next module when done
                continue

            if len(module.xpath('.//a[@class="aalink"]')) > 0:
                # resource is a link
                res = module.xpath('.//a[@class="aalink"]')[0]
            else:
                # resource is not a link, likely restricted
                res = module.xpath('.//div[@class="activityinstance"]')[0]

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

            # write resource text if any in list
            for text in module.xpath('.//div[@class="contentafterlink"]//text()'):
                f.write(" " * 2 + "- %s\n" % text)

        # write newline
        f.write("\n")

    # close file
    f.close()

# create login session
session = login_sess()

# write site content to file
fetch_page(session, "00010", "records/A.txt")
fetch_page(session, "00011", "records/B.txt")
fetch_page(session, "00012", "records/C.txt")
fetch_page(session, "00013", "records/D.txt")
fetch_page(session, "00014", "records/E.txt")
fetch_page(session, "00015", "records/F.txt")

print("[+] Fetching sites done!")
