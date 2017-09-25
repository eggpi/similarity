#!/usr/bin/env python

'''
Build a TF-IDF model out of Wikitext.

Usage:
    compute_features.py <model_directory>
        [--train_documents=<t>]
        [--validation_documents=<v>]
        [--train_fraction=<f>]
        [--n_svd_components=<s>]
        [--reuse_model]
        [--reuse_ngrams]
        [--reuse_train_documents]
        [--profile]

Options:
    --train_documents=<t>       Path to a directory containing training files.
    --validation_documents=<v>  Path to a directory containing validation files.
    --train_fraction=<f>        What fraction of training data to use [default: 1.0].
    --reuse_model               Whether to reuse an existing model or overwrite it.
    --reuse_ngrams              Whether to reuse n-grams from an existing model.
    --reuse_train_documents     Whether to reuse the training documents.
    --n_svd_components=<s>      How many components to truncate themodel to [default: 0].
    --profile                   Turn on profiling.
'''

import model

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.externals import joblib
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import Normalizer
from sklearn.pipeline import make_pipeline

import cProfile
import cStringIO as StringIO
import docopt
import json
import os
import pstats
import random
import multiprocessing

# Thanks, StackOverflow! https://stackoverflow.com/questions/600268
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

MAX_EXCEPTIONS_PER_DOC = 20
SECTIONS_TO_REMOVE = ('references', 'see also', 'external links', 'footnotes')

def load_train_docs():
    documents = []
    for filename in os.listdir(o.train_documents):
        documents.append(model.LazyDoc(
            os.path.join(o.train_documents, filename)))
        if len(documents) % 100 == 0:
            print '\rloaded %d documents' % len(documents),
    print '\rloaded %d documents' % len(documents)
    random.shuffle(documents)
    n_train_documents = int(o.train_fraction * len(documents))
    return documents[:n_train_documents]

def update_ngram_cache(new_cache_tuples, ngram_cache):
    changed = False
    for k, v in new_cache_tuples:
        if k not in ngram_cache or v != ngram_cache[k]:
            ngram_cache[k] = v
            changed = True
    return changed

def analyze_lazy_doc(doc):
    if o.reuse_ngrams and doc.filename in ngram_cache:
        return doc.filename, ngram_cache[doc.filename]
    analyzer = vectorizer.build_analyzer()
    ngrams = analyzer(doc)
    return doc.filename, ngrams

m = None
vectorizer = None
ngram_cache = {}

def main():
    global m
    global vectorizer
    global ngram_cache

    profiler = None
    if o.profile:
        profiler = cProfile.Profile()
        profiler.enable()

    assert os.path.isdir(o.model_directory)
    model_path = os.path.join(o.model_directory, 'model.pkl')
    ngram_cache_path = os.path.join(o.model_directory, 'ngram_cache.json')

    existing_model = None
    if o.reuse_model or o.reuse_train_documents and os.path.exists(model_path):
        print 'loading existing pickled model: ' + o.model_directory
        existing_model = joblib.load(model_path)

    if o.reuse_model:
        m = existing_model
    else:
        print '--reuse_model was NOT passed, will train a new model'
        if o.reuse_ngrams:
            with open(ngram_cache_path) as ngram_cache_file:
                ngram_cache = json.load(ngram_cache_file)
            print 'reusing n-grams for %d documents' % len(ngram_cache)
        vectorizer = TfidfVectorizer(
            input='file', strip_accents = 'unicode', analyzer = 'word',
            tokenizer = model.WikitextStemmingTokenizer(),
            stop_words = 'english', sublinear_tf = True, use_idf = True,
            min_df = 0.0001, max_df = 0.20, norm = 'l2')

        if o.reuse_train_documents and hasattr(existing_model, 'train_documents'):
            train_documents = existing_model.train_documents
            print 'reusing %d train documents' % len(train_documents)
        else:
            train_documents = load_train_docs()
        del existing_model

        print 'analyzing documents in parallel...'
        pool = multiprocessing.Pool()
        new_ngram_cache = pool.imap_unordered(analyze_lazy_doc, train_documents)
        if update_ngram_cache(new_ngram_cache, ngram_cache):
            print 'ngram cache changed, writing down...'
            with open(ngram_cache_path, 'w') as ngram_cache_file:
                json.dump(ngram_cache, ngram_cache_file)

        print 'fitting documents...'
        old_analyzer, vectorizer.analyzer = (
            vectorizer.analyzer, lambda d: ngram_cache[d.filename])
        repository = vectorizer.fit_transform(train_documents).astype(
            np.float16)  # save some memory
        vectorizer.analyzer = old_analyzer

        # don't need this stuff anymore, let's save some memory
        ngram_cache.clear()
        del vectorizer.stop_words_

        print '%d words in the vocabulary, sample: %r' % (
            len(vectorizer.vocabulary_),
            random.sample(vectorizer.vocabulary_.keys(), 300))
        vectorizer.tokenizer = vectorizer.tokenizer.text_tokenizer()

        if int(o.n_svd_components):
            print 'performing SVD step (%s components)...' % o.n_svd_components
            svd = TruncatedSVD(int(o.n_svd_components), algorithm = 'arpack')
            lsi = make_pipeline(svd, Normalizer(norm = 'l2', copy = False))
            repository = lsi.fit_transform(repository)

            explained_variance = svd.explained_variance_ratio_.sum()
            print 'explained variance of the SVD step: %.2f%%' % (
                explained_variance * 100)
            pipeline = make_pipeline(vectorizer, lsi)
        else:
            pipeline = vectorizer

        m = model.Model(repository, pipeline, train_documents)
        joblib.dump(m, model_path)

    ok = 0
    for n, test_file in enumerate(os.listdir(o.validation_documents)):
        with open(os.path.join(o.validation_documents, test_file)) as f:
            tdocs, similarities = m.search(f)
            matches = ', '.join(
                tdoc['title'] + ' [' + tdoc['pageid'] + ']'
                for tdoc in tdocs)
            print '%s -> %s (similarities = %s)' % (
                test_file, matches, similarities),
            if any(td['pageid'] == test_file for td in tdocs):
                print 'OK'
                ok += 1
            else: print
    print '%d / %d' % (ok, n + 1)

    if profiler:
        profiler.disable()
        s = StringIO.StringIO()
        stats = pstats.Stats(profiler, stream=s)
        stats.sort_stats('cumulative').print_stats(30)
        print s.getvalue()

if __name__ == '__main__':
    arguments = docopt.docopt(__doc__)
    class Options(object):
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    o = Options(**dict(
        train_fraction = float(arguments['--train_fraction']), **{
        k.strip('--<>'): v for k, v in arguments.items()
        if k not in ['--train_fraction']
    }))
    main()
