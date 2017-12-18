import flask
import requests
import newspaper

import json
import os
import re

app = flask.Flask(__name__,
    template_folder = os.path.join('server', 'templates'))
app.config['JSON_AS_ASCII'] = False

ELASTICSEARCH_SEARCH_URL = (
    'http://tools-elastic-01.tools.eqiad.wmflabs:80/similarity/_search')
ELASTICSEARCH_AUTH_FILE = (
    '/data/project/similarity/.elasticsearch.ini')
app.elasticsearch_auth = None
if os.path.isfile(ELASTICSEARCH_AUTH_FILE):
    auth_dict = {k.strip(): v.strip(' \n"')
        for line in open(ELASTICSEARCH_AUTH_FILE).readlines()
        for k, v in [line.split('=', 1)]}
    app.elasticsearch_auth = (auth_dict['user'], auth_dict['password'])

COLLAPSE_SPACES_REGEX = re.compile(r'\s+')

def collapse_spaces(text):
    return COLLAPSE_SPACES_REGEX.sub(' ', text)

def page_html_to_text(html, url):
    article = newspaper.Article(url = url)
    article.set_html(html)
    article.parse()
    description = article.meta_description
    text = article.text
    return collapse_spaces(description), collapse_spaces(text)

@app.route('/search', methods = ['POST'])
def search():
    if 'html' not in flask.request.form or not flask.request.form['html']:
        return ('POST some data with a "html" form key\n', 400, '')
    html = flask.request.form['html']
    url = flask.request.form.get('url', '')
    description, text = page_html_to_text(html, url)

    # TODO Log the url (or even text?), and search results

    if not text:
        return flask.jsonify([])
    res = requests.post(ELASTICSEARCH_SEARCH_URL, json.dumps({
        'size': 10,
        'min_score': 20,
        'query': {
            'bool': {
                'must': {
                    'more_like_this': {
                        'like_text': text,
                        'fields': ['text'],
                        'max_doc_freq': 10000,
                    }
                },
                'should': {
                    'match': {
                        'text': description,
                    }
                }
            }
        }
    }), auth = app.elasticsearch_auth).json()
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
