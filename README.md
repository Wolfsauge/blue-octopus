# Overview

* this repository maintains a script for archiving legacy web content for long-term storage

# Installation

* the blue_octopus.py script needs some Python modules to work
* install the needed modules and their dependencies as you see fit
    - [urllib3](https://pypi.org/project/urllib3/)
    - [Beautiful Soup](https://pypi.org/project/beautifulsoup4/)
    - [ftfy](https://pypi.org/project/ftfy/)

* if you have Poetry, use this command
```
$ poetry install
```

# Usage

* the built-in help shows the available options

```
 ./blue_octopus.py -h                                                                                                         
usage: blue_octopus.py [-h] [-u URL] [-p PAGES] [-t THREADS] [-v] [-d]

options:
  -h, --help            show this help message and exit
  -u URL, --url URL     scrape URL (ROOT_URL variable in script)
  -p PAGES, --pages PAGES
                        scrape number of PAGES of content (default 20)
  -t THREADS, --threads THREADS
                        scrape with THREADS consumers (default 8)
  -v, --verbose         Be verbose
  -d, --debug           Be more verbose
```

* the script is called like this, depending on the input it can run several minutes

```
$ ./blue_octopus.py \
    -v \
    -u 'https://legacywebsite.com/community/forums/8/?order=reply_count&direction=desc' \
    -p 1 \
    -t 3
Writing to file result.json. 
```
* the script will work on the task concurrently:
    * it will download the content
    * it will use ftfy recursively to fix multi-level mojibake
    * it will arrange the content as a list of lists
    * it will represent the content as JSON in a UTF-8 encoded file named `result.json`
    * when doing so, it will **overwrite** an existing `result.json` file in the current working directory

* the script will append to the log file `octopus.log` in the current working directory
    * without the `-v` or `--verbose` option it will only log errors
    * you can follow the tail of this log file in another window

```
$ tail -f octopus.log                                                                                                             
2023-10-13T18-04-55-UTC+0200:INFO:CONSUMER:2:TERMINATING
2023-10-13T18-04-55-UTC+0200:INFO:REQUEST:1:{"urllib3":0.1306760311126709,"status":200,"bs":0.014576911926269531,"url":"https://legacywebsite.com/community/threads/29395944959/"}
2023-10-13T18-04-55-UTC+0200:INFO:CONSUMER:1:EOQ
2023-10-13T18-04-55-UTC+0200:INFO:CONSUMER:1:DEQUEUED:21
2023-10-13T18-04-55-UTC+0200:INFO:CONSUMER:1:TERMINATING
2023-10-13T18-04-56-UTC+0200:INFO:REQUEST:0:{"urllib3":0.20589113235473633,"status":200,"bs":0.013968944549560547,"url":"https://legacywebsite.com/community/threads/29393945959/"}
2023-10-13T18-04-56-UTC+0200:INFO:CONSUMER:0:EOQ
2023-10-13T18-04-56-UTC+0200:INFO:CONSUMER:0:DEQUEUED:15
2023-10-13T18-04-56-UTC+0200:INFO:CONSUMER:0:TERMINATING
2023-10-13T18-04-56-UTC+0200:INFO:INIT:ALL CONSUMERS JOINED
^C 
```

# Known Bugs
* use a buck slip data object to pass the parameters around instead of using seven function parameters (R0913)
* get rid of global variables (W0603)

# Feature Wishlist
* save a better audit trail, e.g.:
    * for each fragment, save the URL, where the content has been fetched from exactly
    * consider dumping an additional file `result-annotated.json` containing the audit trail details
    * alternatively, a jq script could be used to transform `result-annotated.json` into the desired `result.json` format
    * do not apply ftfy fixes blindly, but save the old version, too, if ftfy found fixables
    * include more info for ftfy fixes at INFO log severity and story level
* save stats for the bytes transferred in the web requests
* unify log format
* rework the producer, consumer pattern implementation
    * use aiohttp, asyncio, respectively the asyncio.gather() function, instead of the low-level Threads
    * evaluate concurrent.futures instead of the low-level Threads
* HTTP/1.1 pipelining
* write unit tests
* write integration tests

# Pylint Output
```
$ pylint blue_octopus.py
************* Module blue_octopus
blue_octopus.py:83:0: R0913: Too many arguments (6/5) (too-many-arguments)
blue_octopus.py:151:0: R0913: Too many arguments (7/5) (too-many-arguments)
blue_octopus.py:234:4: W0603: Using the global statement (global-statement)

------------------------------------------------------------------
Your code has been rated at 9.80/10 (previous run: 9.80/10, +0.00)
```

# Ruff Output
```
$ ruff blue_octopus.py 
blue_octopus.py:233:89: E501 Line too long (90 > 88 characters)
Found 1 error.
```
