#!/usr/bin/env python

import os
import sys
import json
import requests
import multiprocessing
import mwparserfromhell as mwp

ES_URL = 'http://localhost:9200'

SECTIONS_TO_REMOVE = set([
    'references', 'see also', 'external links', 'footnotes'
])

def put_document(path):
    id = os.path.basename(path)
    doc = json.load(file(path))
    wdoc = mwp.parse(doc['wikitext'])
    for section in wdoc.get_sections(include_headings = True):
        try:
            title = section.get(0).title.strip().lower()
            if title in SECTIONS_TO_REMOVE:
                wdoc.remove(section)
        except (IndexError, AttributeError):
            # No heading or empty section?
            pass
    doc['wikitext'] = wdoc.strip_code()
    response = requests.put(
        ES_URL + '/' + sys.argv[2] + '/' + id, json.dumps(doc))
    print response.content

pool = multiprocessing.Pool()
pool.map(put_document, [
    os.path.join(sys.argv[1], id)
    for id in os.listdir(sys.argv[1])])
