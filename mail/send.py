#!/usr/bin/env python3

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from base64 import urlsafe_b64encode as b64encode

import pickle
import os
import os.path

# initialize multi part message
message = MIMEMultipart()

# set message headers
with open('header.txt') as f:
    headers = [ x.split(':')[1].strip() for x in f.readlines() ]
message['Subject'] = headers[0]
message['From'] = headers[1]
message['To'] = headers[2]

# set html message
with open('body.html') as f:
    msg = MIMEText(f.read(), 'html')
message.attach(msg)

# set attachments
files = [ os.path.join('attachments', f) for f in os.listdir('attachments') ]
for f in files:
    with open(f, 'rb') as fp:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(fp.read())
    encoders.encode_base64(part)
    filename = os.path.basename(f)
    part.add_header('Content-Disposition', 'attachment', filename=filename)
    message.attach(part)

# encode message
body = {
    'raw': b64encode(message.as_bytes()).decode()
}

# load gmail token
with open('token.pickle', 'rb') as token:
    creds = pickle.load(token)

# send the email
service = build('gmail', 'v1', credentials=creds)
message = (service.users().messages().send(userId='me', body=body).execute())
print('[+] Message ID: %s' % message['id'])
