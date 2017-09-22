#!/usr/bin/env python

'''
A TF-IDF model of Wikitext.
'''

import numpy as np
from sklearn.metrics.pairwise import linear_kernel
from nltk.stem.snowball import EnglishStemmer
from nltk import word_tokenize
import mwparserfromhell as mwp

import json
import os
import string

class StemmingTokenizer(object):
    def __init__(self):
        self._stemmer = EnglishStemmer()

    def __call__(self, doc):
        wdoc = mwp.parse(doc)
        for section in wdoc.get_sections(include_headings = True):
            try:
                title = section.get(0).title.strip().lower()
                if title in SECTIONS_TO_REMOVE:
                    wdoc.remove(section)
            except (IndexError, AttributeError):
                # No heading or empty section?
                pass

        tokens = []
        for w in word_tokenize(wdoc.strip_code()):
            t = self._stemmer.stem(w)
            t = t.strip(string.punctuation + string.digits)
            if len(t) > 3 and '|' not in t:
                tokens.append(t)
        return tokens

class LazyDoc(object):
    def __init__(self, filename):
        self.filename = os.path.abspath(filename)
        self._cached_keys = {}

    def _load_doc(self):
        with open(self.filename) as f:
            doc = json.load(f)
        self._cached_keys['pageid'] = doc['pageid']
        self._cached_keys['title'] = doc['title']
        self._cached_keys['url'] = doc['url']
        return doc

    def read(self):
        return self._load_doc()['wikitext']

    def __getitem__(self, key):
        if key in self._cached_keys:
            return self._cached_keys[key]
        return self._load_doc()[key]

class Model(object):
    def __init__(self, repository, transformer, train_documents):
        self.repository = repository
        self.transformer = transformer
        self.train_documents = np.array([{
            'title': lazy_doc['title'],
            'url': lazy_doc['url'],
            'pageid': lazy_doc['pageid'],
        } for lazy_doc in train_documents])

    def search(self, text):
        fv = self.transformer.transform([text])
        search_result = linear_kernel(fv, self.repository).flatten()
        indexes = np.argpartition(search_result, -3)[-3:]
        indexes = indexes[np.argsort(search_result[indexes])]
        return self.train_documents[indexes], search_result[indexes]
