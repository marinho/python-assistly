import datetime
import simplejson
import oauth2 as oauth

from models import RESULTS_MODELS

class AssistlyResponse(object):
    def __init__(self, data=None):
        if data:
            try:
                self.json_data = simplejson.loads(data)
            except simplejson.JSONDecodeError:
                raise Exception(data) # XXX
        else:
            self.json_data = {}
    
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

    def __add__(self, other):
        if isinstance(other, AssistlyResponse):
            new = AssistlyResponse()
            new.json_data = self.json_data.copy()
            new.json_data['results'].extend(other.json_data['results'])
            return new
        raise TypeError('AssistlyResponse can sum only to other AssistlyResponse.')

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

def encode_value(value):
    """Function used to encode values before to send as part of a URL."""
    if isinstance(value, datetime.datetime):
        value = value.strftime('%Y-%m-%dT%H:%M:%SZ')
    elif isinstance(value, datetime.date):
        value = value.strftime('%Y-%m-%d')
    elif isinstance(value, unicode):
        value = value.encode('utf-8')
    return value

