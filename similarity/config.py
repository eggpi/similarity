import os
import types

_ELASTICSEARCH_HOST = os.environ.get(
    'SIMILARITY_ELASTICSEARCH_HOST',
    'http://elasticsearch.svc.tools.eqiad1.wikimedia.cloud')
_ELASTICSEARCH_INDEX = 'similarity'
_ELASTICSEARCH_TYPE = 'needs_references'

_ELASTICSEARCH_AUTH_FILE = '/data/project/similarity/.elasticsearch.ini'

def _load_elasticsearch_auth():
    if os.path.isfile(_ELASTICSEARCH_AUTH_FILE):
        auth_dict = {k.strip(): v.strip(' \n"')
            for line in open(_ELASTICSEARCH_AUTH_FILE).readlines()
            for k, v in [line.split('=', 1)]}
        return (auth_dict['user'], auth_dict['password'])
    return None

config = types.SimpleNamespace(
    elasticsearch_host = _ELASTICSEARCH_HOST,
    elasticsearch_index = _ELASTICSEARCH_INDEX,
    elasticsearch_type = _ELASTICSEARCH_TYPE,
    elasticsearch_search_url = (
        _ELASTICSEARCH_HOST + '/' + _ELASTICSEARCH_INDEX + '/_search'),
    elasticsearch_auth = _load_elasticsearch_auth())
