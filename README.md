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
$ pip install -r similarity/requirements.txt
```

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
