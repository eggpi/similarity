#!/usr/bin/env python

'''
A TF-IDF model of Wikitext.
'''

import numpy as np
from sklearn.utils.extmath import safe_sparse_dot
from nltk.stem.snowball import EnglishStemmer
from nltk import word_tokenize
import mwparserfromhell as mwp

import json
import os
import string

class StemmingTokenizer(object):
    def __init__(self):
        self._stemmer = EnglishStemmer()

    def text_tokenizer(self):
        return self

    def __call__(self, doc):
        tokens = []
        for w in word_tokenize(doc):
            t = self._stemmer.stem(w)
            t = t.strip(string.punctuation + string.digits)
            if len(t) > 3 and '|' not in t:
                tokens.append(t)
        return tokens

class WikitextStemmingTokenizer(object):
    SECTIONS_TO_REMOVE = set([
        'references', 'see also', 'external links', 'footnotes'
    ])

    def __init__(self):
        self._tokenizer = StemmingTokenizer()

    def text_tokenizer(self):
        return self._tokenizer

    def __call__(self, doc):
        wdoc = mwp.parse(doc)
        for section in wdoc.get_sections(include_headings = True):
            try:
                title = section.get(0).title.strip().lower()
                if title in self.SECTIONS_TO_REMOVE:
                    wdoc.remove(section)
            except (IndexError, AttributeError):
                # No heading or empty section?
                pass
        return self._tokenizer(wdoc.strip_code())

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
        # Note: the canonical way of performing this lookup would be to just use
        # linear_kernel. However, that function performs argument type checking
        # which, as a side effect, copies self.repository and casts it up to
        # dtype = np.float, using more memory than we can afford.
        # We know in this case that the operands of the multiplication are
        # compatible, so we just skip the checking and go straight to
        # safe_sparse_dot, making sure to cast fv appropriately so the result is
        # a np.float32, not np.float64.
        fv = self.transformer.transform([text]).astype(np.float16)
        search_result = safe_sparse_dot(
            fv, self.repository.T, dense_output = True)
        search_result.shape = search_result.shape[1]  # flatten without copy
        indexes = np.argpartition(search_result, -5)[-5:]
        indexes = indexes[np.argsort(search_result[indexes])]
        return self.train_documents[indexes], search_result[indexes]
