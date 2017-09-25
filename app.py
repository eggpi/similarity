import model
import lxml_utils

import flask
import lxml.html
from sklearn.externals import joblib

import os
import cStringIO as StringIO

app = flask.Flask(__name__)
app.config['JSON_AS_ASCII'] = False
model_path = os.environ.get(
    'SIMILARITY_MODEL',
    os.path.expanduser(os.path.join('~', 'model.pkl')))
Model = model.Model  # need this to unpickle
m = joblib.load(model_path)

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
]

def html_to_text(html):
    assert isinstance(html, unicode)
    tree = lxml.html.parse(
        StringIO.StringIO(html.encode('utf-8')),
        parser = lxml.html.HTMLParser(
            encoding = 'utf-8', remove_comments = True)).getroot()
    description = tree.cssselect('meta[name="description"]')
    if description:
        # TODO would be cool to boost this in the search somehow
        description = description[0].get('content')
    for s in CSS_SELECTORS_TO_REMOVE:
        for e in tree.cssselect(s):
            lxml_utils.remove_element(e)
    return description + '\n' + tree.text_content()

@app.route('/search', methods = ['POST'])
def search():
    if 'text' not in flask.request.form or not flask.request.form['text']:
        return ('POST some data with a "text" form key\n', 400, '')
    html = flask.request.form['text']
    text = html_to_text(html).encode('utf-8')
    matches, similarities = m.search(StringIO.StringIO(text))
    return flask.jsonify([{
        'title': match['title'],
        'url': match['url'],
        'similarity': str(s),
    } for match, s in zip(matches, similarities)])

@app.route('/', methods = ['GET', 'POST'])
def similarity():
    return flask.render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = 'DEBUG' in os.environ
    app.run(host = '0.0.0.0', port = port, debug = debug, threaded = True)
