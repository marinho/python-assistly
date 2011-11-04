class Model(object):
    data_key = None

    def __init__(self, info):
        info = info[self.data_key] if self.data_key else info

        for k,v in info.items():
            setattr(self, k, v)

    def __unicode__(self):
        return unicode(str(self))

class User(Model):
    data_key = 'user'

    def __str__(self):
        return self.name

class Case(Model):
    data_key = 'case'

    def __str__(self):
        return self.subject

class Topic(Model):
    data_key = 'topic'

    def __str__(self):
        return self.name

class Interaction(Model):
    data_key = 'interaction'

    def __init__(self, info):
        super(Interaction, self).__init__(info)

        for k,v in info.items():
            if k != self.data_key:
                setattr(self, k, v)

    def __str__(self):
        return self.name

