import model

import flask
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

@app.route('/', methods = ['GET', 'POST'])
def similarity():
    if flask.request.method == 'GET':
        return flask.render_template('index.html')
    if 'text' not in flask.request.form or not flask.request.form['text']:
        return ('POST some data with a "text" form key\n', 400, '')
    text = flask.request.form['text'].encode('utf-8')
    matches, _ = m.search(StringIO.StringIO(text))
    return flask.jsonify([{
        'title': match['title'],
        'url': match['url'],
    } for match in matches])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = 'DEBUG' in os.environ
    app.run(host = '0.0.0.0', port = port, debug = debug, threaded = True)
