#!/usr/bin/env python

'''
Fetch the plaintext of Wikipedia pages.

Given a Petscan query, this script will query the Wikipedia API
(with the TextExtract extension), download the plaintext representation of
those pages and load them into ElasticSearch.

Usage:
    parse_live.py <petscan_id> <elasticsearch_url>

Where <elasticsearch> is of the form https://<host>:<port>/<alias>/<type>.
This script will ensure the <alias> exists, create an index named
<alias>_<current time> and move the alias to point to it.
'''

from __future__ import unicode_literals

import docopt
import mwparserfromhell as mwp
import requests
import yamwapi

import functools
import itertools
import json
import multiprocessing
import os
import sys
import time
import traceback
from datetime import datetime

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

INDEX_DATE_FORMAT = '%Y%m%d%H%M'

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

def move_elasticsearch_alias(es_base_url, es_alias, new_index_name):
    move_req = {'actions': []}
    old_indexes_res = requests.get(es_base_url + '/*/_alias/' + es_alias).json()
    if 'error' not in old_indexes_res:
        # Do a few sanity checks since we share an ES cluster with other users,
        # and we *really* don't want to drop other people's data!
        assert len(old_indexes_res) == 1
        assert '*' not in old_indexes_res, old_indexes_res
        assert '_all' not in old_indexes_res, old_indexes_res
        for idx in old_indexes_res:
            assert idx.startswith(es_alias)
            move_req['actions'].append({'remove_index': {'index': idx}})

    move_req['actions'].append(
        {'add': {'index': new_index_name, 'alias': es_alias}})
    move_res = requests.post(
        es_base_url + '/_aliases', json.dumps(move_req))
    move_res.raise_for_status()
    assert 'error' not in move_res.json(), (move_req, move_res)

def main(petscan_id, elasticsearch_url):
    petscan_response = requests.get(
        'https://petscan.wmflabs.org?format=json&psid=' + petscan_id)
    pageids = [obj['id'] for obj in petscan_response.json()['*'][0]['a']['*']]
    print 'loading %d pages...' % len(pageids)
    chunksz = 32  # how many pageids to query the API at a time
    tasks = [pageids[i:i + chunksz] for i in range(0, len(pageids), chunksz)]

    es_base_url, es_alias, es_type = elasticsearch_url.rsplit('/', 2)
    date_str = datetime.now().strftime(INDEX_DATE_FORMAT)
    new_index_name = '%s_%s' % (es_alias, date_str)
    new_index_url = '%s/%s/%s' % (es_base_url, new_index_name, es_type)

    pool = multiprocessing.Pool(
        initializer = initializer, initargs = (new_index_url,))
    pool.map(work, tasks)
    move_elasticsearch_alias(es_base_url, es_alias, new_index_name)

if __name__ == '__main__':
    start = time.time()
    arguments = docopt.docopt(__doc__)
    ret = main(arguments['<petscan_id>'], arguments['<elasticsearch_url>'])
    print 'all done in %d seconds.' % (time.time() - start)
