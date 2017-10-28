import lxml_utils

import flask
import lxml.html
import requests
from sklearn.externals import joblib

import json
import os
import cStringIO as StringIO

app = flask.Flask(__name__)
app.config['JSON_AS_ASCII'] = False

CSS_SELECTORS_TO_REMOVE = [
    '.hidden',
    '.robots-nocontent',
    'footer',
    'header',
    'link',
    'nav',
    'noindex',
    'script',
    'style',
    'img',
]

import re

URL_REGEX_TO_SELECTOR = {
    re.compile('theguardian.com/.+'): '*[data-test-id=article-review-body]',
    re.compile('irishtimes.com/.+'): '.article_bodycopy',
    re.compile('npr.org/.+'): '#storytext',
    re.compile('washingtonpost.com/.+'): 'article',
    re.compile('nytimes.com/.+'): '#story',
    re.compile('arstechnica.(com|co.uk)/.+'): '.article-content',
    re.compile('economist.com/.+'): 'article',
}

COLLAPSE_SPACES_REGEX = re.compile(r'\s+')

def collapse_spaces(text):
    return COLLAPSE_SPACES_REGEX.sub(' ', text)

def html_to_text(html, url=None):
    assert isinstance(html, unicode)
    tree = lxml.html.parse(
        StringIO.StringIO(html.encode('utf-8')),
        parser = lxml.html.HTMLParser(
            encoding = 'utf-8', remove_comments = True)).getroot()
    description = ' '.join(
        tag.get('content')
        for tag in tree.cssselect('meta[name="description"]'))
    if url:
        for r, s in URL_REGEX_TO_SELECTOR.items():
            if r.search(url):
                tree = tree.cssselect(s)[0]
                break
    for s in CSS_SELECTORS_TO_REMOVE:
        for e in tree.cssselect(s):
            lxml_utils.remove_element(e)
    return collapse_spaces(description), collapse_spaces(tree.text_content())

@app.route('/search', methods = ['POST'])
def search():
    if 'html' not in flask.request.form or not flask.request.form['html']:
        return ('POST some data with a "html" form key\n', 400, '')
    html = flask.request.form['html']
    url = flask.request.form.get('url', None)
    description, text = html_to_text(html, url)
    print description
    print text
    res = requests.post('http://localhost:9200/_search', json.dumps({
        'size': 5,
        'query': {
            'bool': {
                'must': {
                    'more_like_this': {
                        'like_text': text,
                        'fields': ['wikitext'],
                        'max_doc_freq': 1000,
                    }
                },
                'should': {
                    'match': {
                        'wikitext': description,
                    }
                }
            }
        }
    })).json()
    return flask.jsonify([{
        'title': h['_source']['title'],
        'url': h['_source']['url'],
        'similarity': h['_score'],
        'pageid': h['_source']['pageid'],
    } for h in res['hits']['hits']])

@app.route('/', methods = ['GET', 'POST'])
def similarity():
    return flask.render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = 'DEBUG' in os.environ
    app.run(host = '0.0.0.0', port = port, debug = debug, threaded = True)
