# Wikipedia Needs References / similarity

A browser extension that tells you when a page you're reading could be used
as a reference in a Wikipedia article. With one click, you can get to an article
and start editing!

Get it from the [Chrome web store](https://chrome.google.com/webstore/detail/wikipedia-needs-reference/michcligfeahibdmakjapmaigojkddmk)
or [Firefox Add-ons](https://addons.mozilla.org/en-GB/firefox/addon/wikipedia-needs-references/).

This repository contains all of the code for both the extension itself
(Wikipedia Needs References) and the backend (similarity), which is hosted in
the [Wikimedia Toolforge](https://tools.wmflabs.org/) and backed by
ElasticSearch.

## Installing on Toolforge

First, make sure to request [ElasticSearch
access](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Elasticsearch).

Clone the repository:

```
$ git clone https://github.com/eggpi/similarity
$ mkdir -p www/python/
$ ln -s ../../similariy www/python/src
```

Create a virtualenv and install the requirements:

```
$ virtualenv -p python3 www/python/venv
$ . www/python/venv/bin/activate
$ pip install --upgrade pip
$ pip install -r similarity/requirements.txt
$ deactivate
```

It may be necessary to run the `pip install -r` command more than once until it
actually works ¯\\\_(ツ)\_/¯

Install the crontab:

```
$ cat similarity/crontab | crontab
```

You also want to run the command in the crontab manually to populate the initial
ElasticSearch dataset.

Now launch the app!

```
$ webservice --backend=kubernetes python start
```
