import urllib
import urllib2
import httplib2
import logging
import simplejson
import oauth2 as oauth
import gzip

try:
    import CStringIO as StringIO
except ImportError:
    import StringIO

from models import User, Case, Topic, Interaction, Customer, RESULTS_MODELS, CASE_STATUS_TYPE_IDS

log = logging.getLogger("assistly")

class OAuthClient(oauth.Client):
    def request(self, uri, method="GET", body='', headers=None, 
        redirections=httplib2.DEFAULT_MAX_REDIRECTS, connection_type=None):
        DEFAULT_POST_CONTENT_TYPE = 'application/x-www-form-urlencoded'

        if not isinstance(headers, dict):
            headers = {}

        if method == "POST":
            headers['Content-Type'] = headers.get('Content-Type', 
                DEFAULT_POST_CONTENT_TYPE)

        is_form_encoded = \
            ((headers.get('Content-Type') == 'application/x-www-form-urlencoded') and (method == "POST"))


        if is_form_encoded and body:
            parameters = oauth.parse_qs(body)
        else:
            parameters = None

        req = oauth.Request.from_consumer_and_token(self.consumer, 
            token=self.token, http_method=method, http_url=uri, 
            parameters=parameters, body=body, is_form_encoded=is_form_encoded)

        req.sign_request(self.method, self.consumer, self.token)

        schema, rest = urllib.splittype(uri)
        if rest.startswith('//'):
            hierpart = '//'
        else:
            hierpart = ''
        host, rest = urllib.splithost(rest)

        realm = schema + ':' + hierpart + host

        #if is_form_encoded: XXX
        #    body = req.to_postdata()
        #elif method == "GET":
        #    uri = req.to_url()
        #else:
        #    headers.update(req.to_header(realm=realm))
        if method == "GET": # XXX
            uri = req.to_url()
        else:
            #body = req.to_postdata()
            headers.update(req.to_header(realm=realm))

        log.debug("URI=%s  METHOD=%s  BODY=%s  HEADERS=%s"
                  % (uri, method, body, headers))
        return httplib2.Http.request(self, uri, method=method, body=body,
            headers=headers, redirections=redirections,
            connection_type=connection_type)

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

    def _request_url(self, method, url, query_params=None, post_params=None, debug_level=None, using_cache=True,
            headers=None):
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
        encoded_post_params = urllib.urlencode(post_params) if post_params else ''

        headers = headers or {}
        if self.accept_gzip and method == 'GET':
            headers['Accept-Encoding'] = 'gzip'

        if method == 'GET':
            full_url = full_url+('?'+encoded_query_params if query_params else '')

        if method in ('PUT','POST'):
            headers['Content-Length'] = str(len(encoded_post_params))

        # Sending request and getting the response
        connection = OAuthClient(self._oauth_consumer, self._oauth_token)
        response, data = connection.request(full_url, method, body=encoded_post_params, headers=headers)
        log.debug("Last request response: %r" % response)
        data = self._uncompress_zip(response, data)

        log.debug("Response data: %r" % data)
        if self.cache_engine and using_cache:
            self.cache_engine.set(key, data)

        return data

    def _uncompress_zip(self, response, data):
        if response.get('content-encoding', None) == 'gzip':
            data = gzip.GzipFile(fileobj=StringIO.StringIO(data)).read()
        return data

    def _get(self, url, params=None):
        return self._request_url('GET', url, params, using_cache=False)

    def _post(self, url, params=None, query_params=None):
        return self._request_url('POST', url, query_params, params, using_cache=False)

    def _put(self, url, params=None, query_params=None):
        return self._request_url('PUT', url, query_params, params, using_cache=False, headers={
            #'Accept': '*/*',
            #'Connection': 'close',
            #User-Agent: OAuth gem v0.4.5
            'Content-Type': 'application/x-www-form-urlencoded',
            #'Host': 'marinho.assistly.com',
            #'Content-Length': 22,
            })

    # API Methods

    def verify_credentials(self):
        return AssistlyResponse(self._get('account/verify_credentials.json'))

    def users(self, count=None, page=None):
        return AssistlyResponse(self._get('users.json', {'count':count, 'page':page}))

    def user_show(self, user_id, return_response=False):
        resp = AssistlyResponse(self._get('users/%s.json'%user_id))
        return resp if return_response else resp.user

    def groups(self, count=None, page=None):
        return AssistlyResponse(self._get('groups.json', {'count':count, 'page':page}))

    def group_show(self, group_id, return_response=False):
        resp = AssistlyResponse(self._get('groups/%s.json'%group_id))
        return resp if return_response else resp.group

    def cases(self, **kwargs):
        return AssistlyResponse(self._get('cases.json', kwargs))

    def case_show(self, case_id, by=None, return_response=False):
        resp = AssistlyResponse(self._get('cases/%s.json'%case_id, {'by':by}))
        return resp if return_response else resp.case

    def case_update(self, case_id, **kwargs):
        if 'case_status_type' in kwargs:
            kwargs['case_status_type_id'] = CASE_STATUS_TYPE_IDS[kwargs.pop('case_status_type')]
        return AssistlyResponse(self._put('cases/%s.json'%case_id, kwargs))

    def topics(self, **kwargs):
        return AssistlyResponse(self._get('topics.json', kwargs))

    def interactions(self, **kwargs):
        return AssistlyResponse(self._get('interactions.json', kwargs))

    def interaction_create(self, **kwargs):
        kwargs.setdefault('interaction_subject', kwargs.pop('subject', None))
        if not kwargs.get('interaction_subject', None):
            raise ValueError('The parameter "interaction_subject" is required.')
        return AssistlyResponse(self._post('interactions.json', kwargs))

    def customers(self, **kwargs):
        return AssistlyResponse(self._get('customers.json', kwargs))

    def customer_create(self, **kwargs):
        return AssistlyResponse(self._post('customers.json', kwargs))

    def customer_show(self, customer_id, return_response=False):
        resp = AssistlyResponse(self._get('customers/%s.json'%customer_id))
        return resp if return_response else resp.customer

    def customer_update(self, customer_id, **kwargs):
        return AssistlyResponse(self._put('customers/%s.json'%customer_id, kwargs))

    def customer_email_create(self, customer_id, email):
        return AssistlyResponse(self._post('customers/%s/emails.json'%customer_id, {'email':email}))

    def customer_email_update(self, customer_id, email_id, new_email):
        return AssistlyResponse(self._put('customers/%s/emails/%s.json'%(customer_id, email_id), {'email':new_email}))

class AssistlyResponse(object):
    def __init__(self, data):
        try:
            self.json_data = simplejson.loads(data)
        except simplejson.JSONDecodeError:
            raise Exception(data) # XXX
    
    def __getattr__(self, name):
        if RESULTS_MODELS.get(name, None):
            value = self.json_data.get(name, None) or self.json_data.get('results', {}).get(name, None)
            if value:
                return RESULTS_MODELS[name](value)

        try:
            return self.json_data[name]
        except KeyError:
            raise AttributeError('Attribute "%s" was not found in the response'%name)

    def __iter__(self):
        for item in self.results:
            yield self._return_as_model(item)

    def __getitem__(self, idx):
        items = self.results[idx]
        if isinstance(items, (tuple,list)):
            self._test = True
            return map(self._return_as_model, items)
        else:
            return self._return_as_model(items)

    def _return_as_model(self, item):
        model = RESULTS_MODELS.get(item.keys()[0], None)
        return model(item[item.keys()[0]]) if model and isinstance(item, dict) else item

