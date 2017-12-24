# similarity

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

It may be necessary to run that last command more than once until it actually works ¯\\\_(ツ)\_/¯

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
