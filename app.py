from server import lxml_utils

import flask
import lxml.html
import requests

import json
import os
import cStringIO as StringIO

app = flask.Flask(__name__,
    template_folder = os.path.join('server', 'templates'))
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

# TODO: Should use proper URL parsing and domain check?
URL_REGEX_TO_SELECTOR = {
    re.compile('arstechnica.(com|co.uk)/.+'): '.article-content',
    re.compile('bbc.(com|co.uk)/.+'): '.story-body__inner > p, .body-content',
    re.compile('cnn.com/.+'): '#body-text',
    re.compile('economist.com/.+'): 'article',
    re.compile('irishtimes.com/.+'): '.article_bodycopy',
    re.compile('newsweek.com/.+'): '.article-body',
    re.compile('npr.org/.+'): '#storytext',
    re.compile('nytimes.com/.+'): '#story',
    re.compile('theatlantic.com/.+'): '.article-body > section',
    re.compile('theguardian.com/.+'): '.content__main-column p',
    re.compile('time.com/.+'): 'article',
    re.compile('washingtonpost.com/.+'): 'article',
}

COLLAPSE_SPACES_REGEX = re.compile(r'\s+')

def collapse_spaces(text):
    return COLLAPSE_SPACES_REGEX.sub(' ', text)

def page_html_to_text(html, url=None):
    assert isinstance(html, unicode)
    tree = lxml.html.parse(
        StringIO.StringIO(html.encode('utf-8')),
        parser = lxml.html.HTMLParser(
            encoding = 'utf-8', remove_comments = True)).getroot()
    description = ' '.join(
        tag.get('content')
        for tag in tree.cssselect('meta[name="description"]'))
    for s in CSS_SELECTORS_TO_REMOVE:
        for e in tree.cssselect(s):
            lxml_utils.remove_element(e)
    wrapper = lxml.html.Element('div')
    if url:
        for r, s in URL_REGEX_TO_SELECTOR.items():
            if r.search(url):
                wrapper.extend(tree.cssselect(s))
                break
    return collapse_spaces(description), collapse_spaces(wrapper.text_content())

@app.route('/search', methods = ['POST'])
def search():
    if 'html' not in flask.request.form or not flask.request.form['html']:
        return ('POST some data with a "html" form key\n', 400, '')
    html = flask.request.form['html']
    url = flask.request.form.get('url', None)
    description, text = page_html_to_text(html, url)
    print description
    print text
    if not text:
        return flask.jsonify([])
    res = requests.post('http://localhost:9200/_search', json.dumps({
        'size': 10,
        'query': {
            'bool': {
                'must': {
                    'more_like_this': {
                        'like_text': text,
                        'fields': ['text'],
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
