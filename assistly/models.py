import re
import datetime

EXP_DATETIME1 = re.compile('^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})Z$')
EXP_DATETIME2 = re.compile('^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})([-+]\d{2}:\d{2})$')

class Model(object):
    def __init__(self, info):
        self._info = info

        for k,v in info.items():
            if k in RESULTS_MODELS and isinstance(v, dict):
                v = RESULTS_MODELS[k](v)
            setattr(self, k, self._decode_value(k, v))

    def __unicode__(self):
        return unicode(str(self))

    def _decode_value(self, key, value):
        # Datetime value
        if isinstance(value, basestring):
            m = EXP_DATETIME1.match(value)
            if not m:
                m = EXP_DATETIME2.match(value)
            if m:
                value = datetime.datetime.strptime(m.group(1)+' '+m.group(2), '%Y-%m-%d %H:%M:%S')
        return value

class User(Model):
    def __str__(self):
        return self.name

class Case(Model):
    def __str__(self):
        return self.subject

class Topic(Model):
    def __str__(self):
        return self.name

class Interaction(Model):
    def __str__(self):
        return self.name or self.body

class Customer(Model):
    def __str__(self):
        return '%s %s'%(self.first_name, self.last_name)

class CustomerEmail(Model):
    def __str__(self):
        return self.email

class Group(Model):
    def __str__(self):
        return self.name

class Article(Model):
    def __str__(self):
        return self.subject

RESULTS_MODELS = {
    'user': User,
    'group': Group,
    'case': Case,
    'topic': Topic,
    'interaction': Interaction,
    'customer': Customer,
    'email': CustomerEmail,
    'article': Article,
    }

CASE_STATUS_TYPE_IDS = {
    'new': 10,
    'open': 30,
    'pending': 50,
    'resolved': 70,
    }

