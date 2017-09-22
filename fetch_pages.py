#!/usr/bin/env python

'''
Fetch the plaintext of Wikipedia pages.

Given a file with one pageid per line, this script will query the Wikipedia API
(with the TextExtract extension) and download the plaintext representation of
those pages.

Usage:
    parse_live.py <pageid-file> <output-dir> [--timeout=<n>]

Options:
    --timeout=<n>    Maximum time in seconds to run for [default: inf].
'''

from __future__ import unicode_literals

import os
import sys

import yamwapi as mwapi

import docopt
import requests

import re
import functools
import itertools
import multiprocessing
import pstats
import shutil
import time
import traceback
import json

USER_AGENT = 'Similarity (https://tools.wmflabs.org/similarity)'
WIKIPEDIA_BASE_URL = 'https://en.wikipedia.org'
WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'
WIKIPEDIA_API_URL = WIKIPEDIA_BASE_URL + '/w/api.php'

MAX_EXCEPTIONS_PER_SUBPROCESS = 5

# Thanks, StackOverflow! https://stackoverflow.com/questions/600268
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def e(s):
    if type(s) == str:
        return s
    return s.encode('utf-8')

def d(s):
    if type(s) == unicode:
        return s
    return unicode(s, 'utf-8')

def query_pageids(wiki, pageids):
    for pageid in pageids:
        params = {
            'pageids': pageid,
            'prop': 'extracts',
            'explaintext': 'true'
        }
        for response in self.wiki.query(params):
            for id, page in response['query']['pages'].items():
                if 'title' not in page:
                    continue
                title = d(page['title'])
                text = page['extract']
                if not text:
                    continue
                text = d(text)
                yield (id, title, text)

# In py3: types.SimpleNamespace
class State(object):
    pass
self = State() # Per-process state

def initializer(output_dir):
    self.output_dir = output_dir
    self.wiki = mwapi.MediaWikiAPI(WIKIPEDIA_API_URL, USER_AGENT)
    self.exception_count = 0

def with_max_exceptions(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwds):
        try:
            return fn(*args, **kwds)
        except:
            traceback.print_exc()
            self.exception_count += 1
            if self.exception_count > MAX_EXCEPTIONS_PER_SUBPROCESS:
                print >>sys.stderr, 'too many exceptions!'
                raise
    return wrapper

@with_max_exceptions
def work(output_dir, pageids):
    rows = []
    results = query_pageids(self.wiki, pageids)
    for pageid, title, wikitext in results:
        url = WIKIPEDIA_WIKI_URL + title.replace(' ', '_')
        with open(os.path.join(self.output_dir, pageid), 'w') as f:
            json.dump({
                'pageid': pageid,
                'url': url,
                'title': title,
                'wikitext': wikitext
            }, f)

def fetch_pages(output_dir, pageids, timeout):
    mkdir_p(output_dir)
    pool = multiprocessing.Pool(
        initializer = initializer, initargs = (output_dir,))

    result = pool.map_async(work, list(pageids))
    pool.close()

    result.wait(timeout)
    if not result.ready():
        print >>sys.stderr, 'timeout, canceling the process pool!'
        pool.terminate()
    pool.join()
    try:
        result.get()
        ret = 0
    except Exception:
        print >>sys.stderr, 'too many exceptions, failed!'
        ret = 1
    return ret

if __name__ == '__main__':
    arguments = docopt.docopt(__doc__)
    pageids_file = arguments['<pageid-file>']
    output_dir = arguments['<output-dir>']
    timeout = float(arguments['--timeout'])
    start = time.time()
    with open(pageids_file) as pf:
        pageids = set(itertools.imap(str.strip, pf))
    ret = fetch_pages(output_dir, pageids, timeout)
    print 'all done in %d seconds.' % (time.time() - start)
    sys.exit(ret)
