import os
import re
import sys
import json
import mwparserfromhell
import multiprocessing
import itertools

def is_news(text):
    return (
        'economist.com' in text
        or 'reuters.com' in text
        or 'cnn.com' in text
        or 'latimes.com' in text
        or 'theguardian.com' in text
        or 'nytimes.com' in text
        or 'businessinsider.com' in text
    )

def print_urls(fname):
    ret = []
    with open(os.path.join(fname)) as f:
        doc = json.load(f)
        wikicode = mwparserfromhell.parse(doc['wikitext'])
        for tpl in wikicode.filter_templates():
            if tpl.name == 'cite':
                try:
                    url = tpl.get('url')
                except ValueError:
                    continue
                if is_news(url.value):
                    ret.append((unicode(url.value), doc['pageid']))

        for tag in wikicode.filter_tags('ref'):
            if not tag.contents:
                continue
            m = re.match('.*\[([^ ]+).*\].*', unicode(tag.contents))
            if m:
                url = m.group(1)
                if is_news(url):
                    ret.append((url, doc['pageid']))
    return ret

wikitext_dir = sys.argv[1]
pool = multiprocessing.Pool()
result = pool.map(print_urls, (
    os.path.join(wikitext_dir, fname)
    for fname in os.listdir(wikitext_dir)
))
for url, pageid in itertools.chain(*result):
    print url.encode('utf-8'), pageid
