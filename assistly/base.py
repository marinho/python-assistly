import urllib
import urllib2
import httplib2
import logging
import oauth2 as oauth
import gzip
from urlparse import parse_qsl

try:
    import CStringIO as StringIO
except ImportError:
    import StringIO

from models import CASE_STATUS_TYPE_IDS
from exceptions import ResourceNotFound, AuthenticationError
from utils import AssistlyResponse

log = logging.getLogger("assistly")

class OAuthClient(oauth.Client):
    disable_ssl_certificate_validation = False

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

        if self.disable_ssl_certificate_validation:
            http_inst = httplib2.Http(disable_ssl_certificate_validation=True)
        else:
            http_inst = httplib2.Http()

        return http_inst.request(uri, method=method, body=body,
            headers=headers, redirections=redirections,
            connection_type=connection_type)

class AssistlyAPI(object):
    _oauth_consumer = None
    _oauth_token = None
    api_version = 1
    debug_level = 0
    accept_gzip = True
    disable_ssl_certificate_validation = False

    def __init__(self, base_url, key=None, secret=None, token_key=None, token_secret=None, api_version=1,
            debug_level=0, accept_gzip=True, cache_engine=None):
        self.api_version = api_version or self.api_version
        self.base_url = self._make_base_url(base_url)
        self.debug_level = debug_level or self.debug_level
        self.accept_gzip = accept_gzip or self.accept_gzip
        self.cache_engine = cache_engine

        if key and secret:
            self.set_consumer(key, secret)

        if token_key and token_secret:
            self.set_token(token_key, token_secret)

    def _get_client(self):
        client = OAuthClient(self._oauth_consumer, self._oauth_token)
        client.disable_ssl_certificate_validation = self.disable_ssl_certificate_validation
        return client

    def _make_base_url(self, base_url):
        if base_url.startswith('http://'):
            base_url = 'https://'+base_url[7:]
        elif not base_url.startswith('https://'):
            base_url = 'https://'+base_url

        if '.desk.com' not in base_url:
            base_url += '.desk.com/'

        return base_url

    def request_token(self):
        if not self._oauth_consumer:
            self.set_consumer(self.key, self.secret)

        client = OAuthClient(self._oauth_consumer)
        client.disable_ssl_certificate_validation = self.disable_ssl_certificate_validation
        resp, content = self._get_client()\
            .request(self._make_url('oauth/request_token', with_api_root=False), 'GET')
        info = dict(parse_qsl(content))

        self.set_token(info['oauth_token'], info['oauth_token_secret'])

    def set_consumer(self, key, secret):
        self.key = key
        self.secret = secret
        self._oauth_consumer = oauth.Consumer(key=self.key, secret=self.secret)

        self._signature_method_plaintext = oauth.SignatureMethod_PLAINTEXT()
        self._signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()

    def set_token(self, token_key, token_secret):
        if not self._oauth_consumer:
            self.set_consumer(self.key, self.secret)

        self._oauth_token = oauth.Token(key=token_key, secret=token_secret)

    def _make_url(self, url, with_api_root=True):
        base_url = self.base_url + ('' if self.base_url.endswith('/') else '/')

        if with_api_root and '/api/v' not in base_url:
            base_url += 'api/v%s/'%self.api_version

        return '%s%s'%(base_url, url)

    def _request_url(self, method, url, query_params=None, post_params=None, debug_level=None, using_cache=True,
            headers=None):
        if self.cache_engine and using_cache:
            key = self.cache_engine.make_key(method, url, query_params, post_params)
            data = self.cache_engine.get(key)
            if data: return data

        if not getattr(self, '_oauth_consumer', None):
            raise AuthenticationError('The OAuth consumer is required.')

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
        response, data = self._get_client()\
            .request(full_url, method, body=encoded_post_params, headers=headers)
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
        return self._request_url('GET', url, params)

    def _post(self, url, params=None, query_params=None):
        return self._request_url('POST', url, query_params, params, using_cache=False)

    def _put(self, url, params=None, query_params=None):
        return self._request_url('PUT', url, query_params, params, using_cache=False, headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            })

    def _delete(self, url, params=None, query_params=None):
        return self._request_url('DELETE', url, query_params, params, using_cache=False)

    # API Methods

    def verify_credentials(self):
        return AssistlyResponse(self._get('account/verify_credentials.json'))

    def users(self, count=None, page=None):
        return AssistlyResponse(self._get('users.json', {'count':count, 'page':page}))

    def user_show(self, user_id, return_response=False):
        resp = AssistlyResponse(self._get('users/%s.json'%user_id))
        try:
            return resp if return_response else resp.user
        except AttributeError:
            raise ResourceNotFound('User "%s" was not found.'%user_id)

    def groups(self, count=None, page=None):
        return AssistlyResponse(self._get('groups.json', {'count':count, 'page':page}))

    def group_show(self, group_id, return_response=False):
        resp = AssistlyResponse(self._get('groups/%s.json'%group_id))
        try:
            return resp if return_response else resp.group
        except AttributeError:
            raise ResourceNotFound('Group "%s" was not found.'%group_id)

    def cases(self, **kwargs):
        return AssistlyResponse(self._get('cases.json', kwargs))

    def case_show(self, case_id, by=None, return_response=False):
        resp = AssistlyResponse(self._get('cases/%s.json'%case_id, {'by':by}))
        try:
            return resp if return_response else resp.case
        except AttributeError:
            raise ResourceNotFound('Case "%s" was not found.'%case_id)

    def case_update(self, case_id, **kwargs):
        if 'case_status_type' in kwargs:
            kwargs['case_status_type_id'] = CASE_STATUS_TYPE_IDS[kwargs.pop('case_status_type')]
        return AssistlyResponse(self._put('cases/%s.json'%case_id, kwargs))

    def topics(self, **kwargs):
        return AssistlyResponse(self._get('topics.json', kwargs))

    def topic_create(self, **kwargs):
        return AssistlyResponse(self._post('topics.json', kwargs))

    def topic_show(self, topic_id, return_response=False):
        resp = AssistlyResponse(self._get('topics/%s.json'%topic_id))
        try:
            return resp if return_response else resp.topic
        except AttributeError:
            raise ResourceNotFound('Topic "%s" was not found.'%topic_id)

    def topic_update(self, topic_id, **kwargs):
        return AssistlyResponse(self._put('topics/%s.json'%topic_id, kwargs))

    def topic_destroy(self, topic_id):
        return AssistlyResponse(self._delete('topics/%s.json'%topic_id))

    def topic_article_create(self, topic_id, **kwargs):
        return AssistlyResponse(self._post('topics/%s/articles.json'%topic_id, kwargs))

    def topic_articles(self, topic_id, **kwargs):
        return AssistlyResponse(self._get('topics/%s/articles.json'%topic_id, kwargs))

    def article_show(self, article_id, return_response=False):
        resp = AssistlyResponse(self._get('articles/%s.json'%article_id))
        try:
            return resp if return_response else resp.article
        except AttributeError:
            raise ResourceNotFound('Article "%s" was not found.'%article_id)

    def article_update(self, article_id, **kwargs):
        return AssistlyResponse(self._put('articles/%s.json'%article_id, kwargs))

    def article_destroy(self, article_id):
        return AssistlyResponse(self._delete('articles/%s.json'%article_id))

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
        try:
            return resp if return_response else resp.customer
        except AttributeError:
            raise ResourceNotFound('Case "%s" was not found.'%case_id)

    def customer_update(self, customer_id, **kwargs):
        return AssistlyResponse(self._put('customers/%s.json'%customer_id, kwargs))

    def customer_email_create(self, customer_id, email):
        return AssistlyResponse(self._post('customers/%s/emails.json'%customer_id, {'email':email}))

    def customer_email_update(self, customer_id, email_id, new_email):
        return AssistlyResponse(self._put('customers/%s/emails/%s.json'%(customer_id, email_id), {'email':new_email}))

    def customer_phone_create(self, customer_id, phone):
        return AssistlyResponse(self._post('customers/%s/phones.json'%customer_id, {'phone':phone}))

    def customer_phone_update(self, customer_id, phone_id, new_phone):
        return AssistlyResponse(self._put('customers/%s/phones/%s.json'%(customer_id, phone_id), {'email':new_phone}))
