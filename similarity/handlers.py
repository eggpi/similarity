from .config import config

import flask
import newspaper
import requests

import json
import re

_COLLAPSE_SPACES_REGEX = re.compile(r'\s+')

def _collapse_spaces(text):
    return _COLLAPSE_SPACES_REGEX.sub(' ', text)

def _page_html_to_text(html, url):
    article = newspaper.Article(url = url)
    article.set_html(html)
    article.parse()
    description = article.meta_description
    text = article.text
    return _collapse_spaces(description), _collapse_spaces(text)

def _query_elasticsearch(text, description):
    return requests.post(config.elasticsearch_search_url, json.dumps({
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
    }), auth = config.elasticsearch_auth).json()

def search():
    if not flask.request.form.get('html', ''):
        return ('POST some data with a "html" form key\n', 400, '')

    html = flask.request.form['html']
    url = flask.request.form.get('url', '')
    description, text = _page_html_to_text(html, url)
    debug_info = {'description': description, 'html': html, 'text': text}
    response = {'debug': debug_info, 'results': []}

    # TODO Log the url (or even text?), and search results

    if text:
        es_response = _query_elasticsearch(text, description)
        response['results'] = [{
            'title': h['_source']['title'],
            'url': h['_source']['url'],
            'similarity': h['_score'],
            'pageid': h['_source']['pageid'],
        } for h in es_response['hits']['hits']]
    return flask.jsonify(response)
