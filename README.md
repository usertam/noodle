# Project Noodle
This is my personal Moodle web scraper, which is used to keep track of the changes of the configured course sites using Git, and to download the latest changed files from the updated sites.

## Preparation

### Install nessesary packages
```sh
python3 -m pip install -r requirements.txt
```

### Configuration
Noodle will authenticate and fetch the sites using `config.json`.  
The config file should resemble the below:
```
{
    "login": [
        {
            "user": "MOODLE_USERNAME",
            "pass": "MOODLE_PASSWORD"
        }
    ],
    "sites": [
        {
            "name": "COURSE_CODE",
            "href": "COURSE_URL"
        }
    ]
}
```

## Usage
```sh
python3 noodle.py
```
