#!/usr/bin/env python3
"""Module providing a command line tool to download legacy web content."""

# Author: Wolfsauge
# Date: 2023-10-08

import sys
import argparse
import logging
import time
import json

from queue import Queue
import threading
from threading import Thread

from urllib.parse import urljoin
import urllib3

from bs4 import BeautifulSoup

my_urllib3_session: urllib3.poolmanager.PoolManager
ROOT_URL = "https://legacywebsite.org/community/forums/8/?order=reply_count&direction=desc"


def write_log_message(severity: int, message: str) -> None:
    """Function emitting a log message using the standard facility."""
    match severity:
        case logging.DEBUG:
            logging.debug(message)
        case logging.INFO:
            logging.info(message)
        case logging.WARNING:
            logging.warning(message)
        case logging.ERROR:
            logging.error(message)
        case logging.CRITICAL:
            logging.critical(message)
        case _:
            print("ERROR")
            sys.exit(1)


def get_soup(url, identifier):
    """Function which returns a beautifulsoup data structure for a URL."""
    # Get data from network
    start_request_time = time.time()
    response = my_urllib3_session.request("GET", url)
    end_request_time = time.time()
    request_duration = end_request_time - start_request_time

    if not (response.status >= 200 and response.status < 300):
        write_log_message(
            logging.ERROR,
            f"REQUEST:{identifier}:ERROR:Received HTTP {response.status} on {url}",
        )

    # Wait for grace
    time.sleep(request_duration)

    # Parse data received from network
    start_parse_time = time.time()
    soup = BeautifulSoup(response.data, "lxml")
    end_parse_time = time.time()
    parse_duration = end_parse_time - start_parse_time

    # Log stats
    my_request_stats = {
        "urllib3": request_duration,
        "status": response.status,
        "bs": parse_duration,
        "url": url,
    }
    my_request_stats_string = json.dumps(my_request_stats, separators=(",", ":"))
    write_log_message(logging.INFO, f"REQUEST:{identifier}:{my_request_stats_string}")

    return soup


def do_producer_work_recursion(
    lock, work_queue, url, pages, page_counter=0, qeventcount=0
):
    """Function for doing the producer's work."""
    soup = get_soup(urljoin(ROOT_URL, url), "P")

    for element in soup.find_all("div", class_="structItem-title"):
        item = element.a.get("href")
        # ORDER: here an order needs to be established
        queue_item = (qeventcount, item)
        work_queue.put(queue_item)
        qeventcount += 1
        write_log_message(logging.DEBUG, f"PRODUCER:QUEUED:{item}")

    page_counter += 1
    next_page = soup.find("a", class_="pageNav-jump pageNav-jump--next")

    if page_counter < pages:
        if next_page is not None:
            next_page_url = next_page.get("href")
            qeventcount = do_producer_work_recursion(
                lock, work_queue, next_page_url, pages, page_counter, qeventcount
            )

    return qeventcount


def producer_function(lock, work_queue, url, pages):
    """Function implementing the producer pattern."""
    write_log_message(logging.INFO, "PRODUCER:STARTING")

    # Do the producer's work
    qeventcount = do_producer_work_recursion(lock, work_queue, url, pages)
    write_log_message(logging.INFO, f"PRODUCER:QUEUED:{qeventcount}")

    # Put signal, when done
    work_queue.put(None)

    write_log_message(logging.INFO, "PRODUCER:TERMINATING")


def parse_story(soup, story):
    """Function to parse a beautiful soup data structure of a story fragment
    into a story element and appending it to the story list. (recursion)"""
    element = soup.find("div", class_="block-body js-replyNewMessageContainer")

    for article in element.find_all(
        "article", class_="message message--post js-post js-inlineModContainer"
    ):
        message_author = article.get("data-author")
        message_text = article.find("div", class_="bbWrapper").text
        story_element = {}
        story_element["author"] = message_author
        story_element["txt"] = message_text
        story.append(story_element)

    return story


def parse_subforum(
    my_ordered_result, lock, work_queue, identifier, url, story, story_id
):
    """Function to recursively parse a subforum and to insert the result into
    the results list using thread locking. (recursion)"""
    soup = get_soup(urljoin(ROOT_URL, url), identifier)

    # Recursively scrape

    # Try to get next page link
    next_page = soup.find("a", class_="pageNav-jump pageNav-jump--next")

    if next_page is not None:
        # Parse content of this page into story
        story = parse_story(soup, story)

        # And then go to the next page
        my_next_url = next_page.get("href")
        parse_subforum(
            my_ordered_result,
            lock,
            work_queue,
            identifier,
            my_next_url,
            story,
            story_id,
        )
    else:
        # We are on the last page
        story = parse_story(soup, story)
        with lock:
            # Critical section
            my_ordered_result.insert(story_id, story)


def do_consumer_recursion(
    my_ordered_result, lock, work_queue, identifier, qeventcount=0
):
    """Function to take a work unit from the shared queue and then doing
    the consumer's work in parallel with other consumers."""
    while True:
        # ORDER: here an order needs to be established
        item = work_queue.get()

        # Handle EOQ signal
        if item is None:
            work_queue.put(item)
            write_log_message(logging.INFO, f"CONSUMER:{identifier}:EOQ")
            break
        qeventcount += 1

        # Do the consumer's work
        write_log_message(logging.DEBUG, f"CONSUMER:{identifier}:RECURSING ON:{item}")
        parse_subforum(
            my_ordered_result, lock, work_queue, identifier, item[1], [], item[0]
        )
        write_log_message(logging.DEBUG, f"CONSUMER:{identifier}:DONE WITH:{item}")
    return qeventcount


def consumer_function(my_ordered_result, lock, work_queue, identifier):
    """Function implementing the consumer pattern."""
    write_log_message(logging.INFO, f"CONSUMER:{identifier}:STARTING")

    qeventcount = do_consumer_recursion(my_ordered_result, lock, work_queue, identifier)
    write_log_message(logging.INFO, f"CONSUMER:{identifier}:DEQUEUED:{qeventcount}")
    write_log_message(logging.INFO, f"CONSUMER:{identifier}:TERMINATING")


def dump_my_result(my_ordered_result):
    """Function to dump the result list into a utf-8 encoded file."""
    file_name = "result.json"
    print(f"Writing to file {file_name}.")
    with open(file_name, "w", encoding="utf-8") as file_pointer:
        json.dump(my_ordered_result, file_pointer)


def main() -> int:
    """Function implementing the one producer, many consumer with shared queue pattern."""
    global my_urllib3_session, ROOT_URL

    my_ordered_result: list = []

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-u",
        "--url",
        type=str,
        default=ROOT_URL,
        help="scrape URL (ROOT_URL variable in script)",
    )
    parser.add_argument(
        "-p",
        "--pages",
        type=int,
        default=20,
        help="scrape number of PAGES of content (default 20)",
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=8,
        help="scrape with THREADS consumers (default 8)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Be verbose",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
    )
    parser.add_argument(
        "-d",
        "--debug",
        help="Be more verbose",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=args.loglevel,
        format="%(asctime)s:%(levelname)s:%(message)s",
        datefmt="%Y-%m-%dT%H-%M-%S-UTC%z",
        filename="octopus.log",
    )

    write_log_message(logging.DEBUG, f"INIT:args:{args}")

    my_urllib3_session = urllib3.PoolManager(num_pools=1, maxsize=16)
    write_log_message(logging.DEBUG, f"INIT:my_urllib3_session:{my_urllib3_session}")

    work_queue: "Queue[str]" = Queue()
    write_log_message(logging.INFO, f"INIT:work_queue:{work_queue}")

    lock = threading.Lock()
    write_log_message(logging.INFO, f"INIT:threading_lock:{lock}:{type(lock)}")

    # Get rid of the global ROOT_URL
    ROOT_URL = args.url

    consumers = [
        Thread(target=consumer_function, args=(my_ordered_result, lock, work_queue, i))
        for i in range(args.threads)
    ]
    write_log_message(logging.INFO, f"INIT:CONSUMER THREADS CREATED {len(consumers)}")

    for consumer in consumers:
        consumer.start()

    write_log_message(logging.INFO, f"INIT:CONSUMER THREADS STARTED {len(consumers)}")

    producer = Thread(
        target=producer_function,
        args=(
            lock,
            work_queue,
            args.url,
            args.pages,
        ),
    )
    write_log_message(logging.INFO, "INIT:SINGLE PRODUCER THREAD CREATED")

    producer.start()
    write_log_message(logging.INFO, "INIT:SINGLE PRODUCER STARTED")

    producer.join()
    write_log_message(logging.INFO, "INIT:SINGLE PRODUCER JOINED")

    for consumer in consumers:
        consumer.join()
    write_log_message(logging.INFO, "INIT:ALL CONSUMERS JOINED")

    dump_my_result(my_ordered_result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
