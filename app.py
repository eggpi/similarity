import similarity

import flask
import requests
import newspaper

import os

app = flask.Flask(__name__,
    template_folder = os.path.join('similarity', 'templates'))
app.config['JSON_AS_ASCII'] = False

app.add_url_rule(
    '/search',
    view_func = similarity.handlers.search,
    methods = ['POST'])

@app.route('/', methods = ['GET', 'POST'])
def similarity():
    return flask.render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = 'DEBUG' in os.environ
    app.run(host = '0.0.0.0', port = port, debug = debug, threaded = True)
