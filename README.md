# Project Noodle
This is my personal Moodle web scraper, during my studies at UOWCHK. Its main purposes are to keep track of the history of the configured course sites using git, and to download the latest uploaded files from parsing the new URLs of the updated pages.

## Preparation

### Install nessesary packages
```sh
python3 -m pip install -r requirements.txt
```

### Store credentials
The credentials will be used to authenticate with Moodle.
```sh
python3 data/secret.py
```

### Configure course sites
Noodle will keep track of all the sites listed in the config.
```sh
nano data/sites.conf
```

## Usage
This will update the local sites. If Noodle does find changes, it will generate a commit and attempt to fetch new files. \
However, if the git repo of local sites does not exist (indicating first use), Noodle will attempt to initialize it.
```sh
python3 noodle.py
```
