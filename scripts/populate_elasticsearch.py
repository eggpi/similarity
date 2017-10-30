#!/usr/bin/env python

'''
Fetch the plaintext of Wikipedia pages.

Given a Petscan query, this script will query the Wikipedia API
(with the TextExtract extension), download the plaintext representation of
those pages and load them into ElasticSearch.

Usage:
    parse_live.py <petscan_id> <elasticsearch_url>
'''

from __future__ import unicode_literals

import docopt
import requests
import yamwapi

import os
import sys
import functools
import itertools
import multiprocessing
import time
import traceback
import json
import mwparserfromhell as mwp

USER_AGENT = 'Similarity (https://tools.wmflabs.org/similarity)'
WIKIPEDIA_BASE_URL = 'https://en.wikipedia.org'
WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'
WIKIPEDIA_API_URL = WIKIPEDIA_BASE_URL + '/w/api.php'

MAX_EXCEPTIONS_PER_SUBPROCESS = 10

SECTIONS_TO_REMOVE = set([
    'bibliography',
    'external links',
    'footnotes',
    'further reading',
    'notes',
    'references',
    'see also',
])

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

def initializer(elasticsearch_url):
    self.es_url = elasticsearch_url
    self.es_session = requests.Session()
    self.wiki = yamwapi.MediaWikiAPI(WIKIPEDIA_API_URL, USER_AGENT)
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
def work(pageids):
    rows = []
    results = query_pageids(self.wiki, pageids)
    for pageid, title, text in results:
        url = WIKIPEDIA_WIKI_URL + title.replace(' ', '_')
        wdoc = mwp.parse(text)
        for section in wdoc.get_sections(include_headings = True):
            try:
                if section.get(0).title.strip().lower() in SECTIONS_TO_REMOVE:
                    wdoc.remove(section)
            except (IndexError, AttributeError):
                # no heading or empty section?
                pass
            esdoc = json.dumps({
                'pageid': pageid,
                'url': url,
                'title': title,
                'text': wdoc.strip_code()
            })
            response = self.es_session.put(self.es_url + '/' + pageid, esdoc)
            response.raise_for_status()

def fetch_pages(petscan_id, elasticsearch_url):
    petscan_response = requests.get(
        'https://petscan.wmflabs.org?format=json&psid=' + petscan_id)
    pageids = [obj['id'] for obj in petscan_response.json()['*'][0]['a']['*']]
    print 'loading %d pages...' % len(pageids)
    chunksz = 32  # how many pageids to query the API at a time
    tasks = [pageids[i:i + chunksz] for i in range(0, len(pageids), chunksz)]
    pool = multiprocessing.Pool(
        initializer = initializer, initargs = (elasticsearch_url,))
    pool.map(work, tasks)

if __name__ == '__main__':
    # TODO: We should actually garbage-collect old data as such:
    # 1) Create a template that auto-adds a "latest" alias to new indices:
    #  curl -XPUT localhost:9200/_template/text_extract_template -d
    #  '{"template": "text_extract_*", "aliases": {"text_extract_latest": {}}}'
    # Seems to be idempotent.
    # 2) PUT data to indexes called text_extract_YYYYMMDD-HHMM
    # 3) Get the current list of indices under the latest alias?
    #  curl -XGET localhost:9200/_alias/text_extract_latest
    # 4) Delete old indices:
    #  curl -XDELETE localhost:9200/text_extract_YYYYMMDD
    # ALTERNATIVE, probably better: just move the alias atomically.
    # https://www.elastic.co/guide/en/elasticsearch/guide/current/index-aliases.html
    # Then don't need to worry about how the search behaves when there
    # is more than one index under same alias (duplicate results?)
    start = time.time()
    arguments = docopt.docopt(__doc__)
    ret = fetch_pages(
            arguments['<petscan_id>'],
            arguments['<elasticsearch_url>'])
    print 'all done in %d seconds.' % (time.time() - start)
