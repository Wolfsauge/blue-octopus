# Installation

* you need some Python modules for blue_octopus.py to work
    - [urllib3](https://pypi.org/project/urllib3/)
    - [Beautiful Soup](https://pypi.org/project/beautifulsoup4/)

```
$ poetry install
```

# Usage

```
$ ./blue_octopus.py \
    -u 'https://legacywebsite.com/community/forums/8/?order=reply_count&direction=desc' \
    -p 1 \
    -t 3
```

* will work on the legacy web content concurrently
    * will download the content
    * will arrange the content as a JSON array of JSON arrays
    * will save the JSON representation in a file named `result.json`
* will write log file to `octopus.log`

# Wishlist

## Bugs
* use a buck slip data object to pass the parameters around instead of using seven function parameters (R0913)
* get rid of global variables (W0603)

## Features
* use ftfy to fix mojibake found in most legacy web content
    * apply ftfy recursively to fix multi-level mojibake
* write unit tests
* write integration tests

## Pylint Output
```
$ pylint blue_octopus.py                                                                                                         
************* Module blue_octopus
blue_octopus.py:80:0: R0913: Too many arguments (6/5) (too-many-arguments)
blue_octopus.py:139:0: R0913: Too many arguments (7/5) (too-many-arguments)
blue_octopus.py:218:4: W0603: Using the global statement (global-statement)

------------------------------------------------------------------
Your code has been rated at 9.78/10 (previous run: 9.78/10, +0.00)
```
