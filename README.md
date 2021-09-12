# Project Noodle
This is my personal Moodle web scraper, which is used to keep track of the changes of the configured course sites using Git, and to download the latest changed files from the updated sites.

## Preparation

### Install nessesary packages
```sh
python3 -m pip install -r requirements.txt
```

### Configuration
Noodle will authenticate and fetch the sites using `config.json`.  
The setup script first asks for the credentials, then will parse the sites automatically.
```sh
python3 noodle_config.py
```

## Usage
```sh
python3 noodle.py
```
