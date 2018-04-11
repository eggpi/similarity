#!/usr/bin/env python3

'''
Fetch the plaintext of Wikipedia pages.

Given a Petscan query, this script will query the Wikipedia API
(with the TextExtract extension), download the plaintext representation of
those pages and load them into ElasticSearch.

Usage:
    populate_elasticsearch.py <petscan_id>
        [--max_es_qps=<n>]

Options:
    --max_es_qps=<n>    How many documents to PUT per second [default: 24].
'''

import toolforge_utils
from config import config

import docopt
import mwapi
import mwparserfromhell as mwp
import requests

import functools
import itertools
import json
import multiprocessing
import os
import sys
import time
import traceback
from datetime import datetime, timedelta

USER_AGENT = 'Similarity (https://tools.wmflabs.org/similarity)'
WIKIPEDIA_BASE_URL = 'https://en.wikipedia.org'
WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'

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
    if type(s) == str:
        return s
    return str(s, 'utf-8')

def query_pageids(wiki, pageids):
    for pageid in pageids:
        params = {
            'action': 'query',
            # We query only one page at a time because that's as much as we're
            # allowed to for full-article requests. We also pass an explicit
            # exlimit=1 to keep a warning from being generated.
            # More context: https://phabricator.wikimedia.org/T102856
            'pageids': pageid,
            'exlimit': 1,
            'prop': 'extracts',
            'explaintext': 'true'
        }
        for response in self.wiki.post(continuation = True, **params):
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

def initializer(es_session, es_url, es_max_qps):
    self.es_url = es_url
    self.es_session = es_session
    self.es_next_request_time = datetime.now()
    self.es_max_qps = es_max_qps
    self.wiki = mwapi.Session(WIKIPEDIA_BASE_URL, user_agent = USER_AGENT)
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
        time.sleep(max(
            0, (self.es_next_request_time - datetime.now()).total_seconds()))
        self.es_next_request_time = datetime.now() + timedelta(
            seconds = 1.0 / self.es_max_qps)
        # TODO Write the full batch using the bulk API in ES
        response = self.es_session.put(self.es_url + '/' + pageid, esdoc)
        response.raise_for_status()

def move_elasticsearch_alias(es_session, es_base_url, es_alias, new_index_name):
    move_req = {'actions': []}
    old_indexes_res = es_session.get(es_base_url + '/*/_alias/' + es_alias).json()
    if 'error' not in old_indexes_res:
        # Do a few sanity checks since we share an ES cluster with other users,
        # and we *really* don't want to drop other people's data!
        assert len(old_indexes_res) <= 1
        assert '*' not in old_indexes_res, old_indexes_res
        assert '_all' not in old_indexes_res, old_indexes_res
        for idx in old_indexes_res:
            assert idx.startswith(es_alias)
            move_req['actions'].append({'remove_index': {'index': idx}})

    move_req['actions'].append(
        {'add': {'index': new_index_name, 'alias': es_alias}})
    move_res = es_session.post(es_base_url + '/_aliases', json.dumps(move_req))
    move_res.raise_for_status()
    assert 'error' not in move_res.json(), (move_req, move_res)

def build_petscan_url(petscan_id):
    four_months_ago = datetime.now() - timedelta(days = 4 * 30)
    return 'https://petscan.wmflabs.org?format=json&psid=%s&after=%s' % (
        petscan_id, four_months_ago.strftime('%Y%m%d'))

def main(petscan_id, max_es_qps):
    es_session = requests.Session()
    es_session.auth = config.elasticsearch_auth

    date_str = datetime.now().strftime(INDEX_DATE_FORMAT)
    new_index_name = '%s_%s' % (config.elasticsearch_index, date_str)
    new_index_url = '%s/%s/%s' % (
        config.elasticsearch_host, new_index_name, config.elasticsearch_type)

    petscan_response = requests.get(build_petscan_url(petscan_id))
    pageids = [obj['id'] for obj in petscan_response.json()['*'][0]['a']['*']]
    chunksz = 32  # how many pageids to query the API at a time
    tasks = [pageids[i:i + chunksz] for i in range(0, len(pageids), chunksz)]

    print('populating elasticsearch alias %s, type %s with %d pages' % (
        config.elasticsearch_index, config.elasticsearch_type, len(pageids)))

    max_qps = float(max_es_qps) / multiprocessing.cpu_count()
    assert max_qps > 0
    pool = multiprocessing.Pool(
        initializer = initializer,
        initargs = (es_session, new_index_url, max_qps))
    pool.map(work, tasks)
    move_elasticsearch_alias(
        es_session, config.elasticsearch_host,
        config.elasticsearch_index, new_index_name)

if __name__ == '__main__':
    arguments = docopt.docopt(__doc__)

    if toolforge_utils.running_in_toolforge():
        # Should match the job's name in crontab
        logfiles = [
            'similarity_update' + '.' + ext for ext in ('out', 'err')
        ]
        for logfile in logfiles:
            file(logfile, 'w').close()  # truncate

    success = True
    start = time.time()
    try:
        main(arguments['<petscan_id>'], int(arguments['--max_es_qps']))
    except BaseException as e:
        print(e, file = sys.stderr)
        success = False

    if toolforge_utils.running_in_toolforge():
        toolforge_utils.email('Similarity update %s after %d seconds!' % (
            'succeeded' if success else 'failed',
            (time.time() - start), logfiles))
