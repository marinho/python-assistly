import urllib
import urllib2
import httplib
import simplejson
import oauth2 as oauth
import gzip

try:
    import CStringIO as StringIO
except ImportError:
    import StringIO

from models import User, Case, Topic, Interaction

class AssistlyAPI(object):
    def __init__(self, base_url, key, secret, token_key=None, token_secret=None, api_version=1, debug_level=0,
            accept_gzip=True, cache_engine=None):
        self.key = key
        self.secret = secret
        self.api_version = api_version
        self.base_url = self._make_base_url(base_url)
        self.debug_level = debug_level
        self.accept_gzip = accept_gzip
        self.cache_engine = cache_engine

        if token_key and token_secret:
            self.set_token(token_key, token_secret)

    def _make_base_url(self, base_url):
        if base_url.startswith('http://'):
            base_url = 'https://'+base_url[7:]
        elif not base_url.startswith('https://'):
            base_url = 'https://'+base_url

        if '.assistly.com' not in base_url:
            base_url += '.assistly.com/'

        if '/api/v' not in base_url:
            base_url += 'api/v%s/'%self.api_version

        return base_url

    def request_token(self):
        # TODO
        self.set_token(None, None)

    def set_token(self, token_key, token_secret):
        self.token_key = token_key
        self.token_secret = token_secret

        self._oauth_consumer = oauth.Consumer(key=self.key, secret=self.secret)
        self._oauth_token = oauth.Token(key=self.token_key, secret=self.token_secret)
        self._signature_method_plaintext = oauth.SignatureMethod_PLAINTEXT()
        self._signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()

    def _make_url(self, url):
        base_url = self.base_url + ('' if self.base_url.endswith('/') else '/')
        return '%s%s'%(base_url, url)

    def _request_url(self, method, url, query_params=None, post_params=None, debug_level=None, using_cache=True):
        if self.cache_engine and using_cache:
            key = self.cache_engine.make_key(method, url, query_params, post_params)
            data = self.cache_engine.get(key)
            if data: return data

        if not getattr(self, '_oauth_consumer', None):
            raise Exception('The OAuth consumer is required.')

        debug_level = debug_level if debug_level is not None else self.debug_level
        full_url = self._make_url(url)

        # Parameter dictionaries
        query_params = dict([(k,v) for k,v in query_params.items() if v is not None]) if query_params else {}
        encoded_query_params = urllib.urlencode(query_params) if query_params else ''

        host = full_url.split('//')[1].split('/')[0]
        resource = full_url[full_url.index(host)+len(host):]
        connection = httplib.HTTPSConnection("%s"%host)

        # OAuth request
        oauth_params = post_params if method in ('POST','PUT') else query_params
        req = oauth.Request.from_consumer_and_token(
                self._oauth_consumer,
                token=self._oauth_token,
                http_method=method,
                http_url=full_url,
                parameters=oauth_params,
                )
        req.sign_request(self._signature_method_hmac_sha1, self._oauth_consumer, self._oauth_token)

        headers = req.to_header()
        if method in ('POST','PUT'):
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        if self.accept_gzip and method == 'GET':
            headers['Accept-Encoding'] = 'gzip'

        if method == 'GET':
            resource_url = resource+('?'+encoded_query_params if query_params else '')
        else:
            resource_url = resource

        if method in ('POST','PUT'):
            raise Exception(req.to_postdata()) # XXX

        # Sending request and getting the response
        connection.request(method, resource_url, body=req.to_postdata(), headers=headers)
        response = connection.getresponse()
        data = self._uncompress_zip(response)

        if method in ('POST','PUT'):
            raise Exception(response.getheaders(), data) # XXX

        if self.cache_engine and using_cache:
            self.cache_engine.set(key, data)

        return data

    def _uncompress_zip(self, response):
        data = response.read()
        headers = dict(response.getheaders())
        if headers.get('content-encoding', None) == 'gzip':
            data = gzip.GzipFile(fileobj=StringIO.StringIO(data)).read()
        return data

    def _get(self, url, params=None):
        return self._request_url('GET', url, params)

    def _post(self, url, params=None, query_params=None):
        return self._request_url('POST', url, query_params, params, debug_level=1, using_cache=False)

    def _put(self, url, params=None, query_params=None):
        return self._request_url('PUT', url, query_params, params)

    # API Methods

    def verify_credentials(self):
        return AssistlyResponse(self._get('account/verify_credentials.json'), result_class=User)

    def users(self, count=None, page=None):
        return AssistlyResponse(self._get('users.json', {'count':count, 'page':page}), result_class=User)

    def cases(self, **kwargs):
        """
        The valid kwargs parameters are:
        - name
        - first_name
        - last_name
        - email
        - phone
        - company
        - twitter
        - labels
        - case_id
        - subject
        - description
        - status
        - priority
        - assigned_group
        - assigned_user
        - channels
        - notes
        - attachments
        - case_custom_key
        - created
        - updated
        - since_created_at
        - max_created_at
        - since_updated_at
        - max_updated_at
        - since_id
        - max_id
        - count
        - page
        """
        return AssistlyResponse(self._get('cases.json', kwargs), result_class=Case)

    def topics(self, **kwargs):
        """
        The valid kwargs parameters are:
        - count
        - page
        """
        return AssistlyResponse(self._get('topics.json', kwargs), result_class=Topic)

    def interactions(self, **kwargs):
        """
        The valid kwargs parameters are:
        - case_id
        - channels
        - since_created_at
        - max_created_at
        - since_updated_at
        - max_updated_at
        - since_id
        - max_id
        - count
        - page
        """
        return AssistlyResponse(self._get('interactions.json', kwargs), result_class=Interaction)

    def interaction_create(self, **kwargs):
        kwargs.setdefault('interaction_subject', kwargs.pop('subject', None))
        if not kwargs.get('interaction_subject', None):
            raise ValueError('The parameter "interaction_subject" is required.')
        return AssistlyResponse(self._post('interactions.json', kwargs), result_class=Interaction)

class AssistlyResponse(object):
    def __init__(self, data, result_class=None):
        self.json_data = simplejson.loads(data)
        self.result_class = result_class or None
    
    def __getattr__(self, name):
        if self.result_class and name == self.result_class.data_key:
            return self.result_class(self.json_data)

        try:
            return self.json_data[name]
        except KeyError:
            raise AttributeError('Attribute "%s" was not found in the response'%name)

    def __iter__(self):
        for item in self.results:
            yield self.result_class(item) if self.result_class else item

    def __getitem__(self, idx):
        items = self.results[idx]
        if isinstance(items, (tuple,list)):
            return [self.result_class(item) if self.result_class else item for item in items]
        else:
            return self.result_class(items) if self.result_class else items

