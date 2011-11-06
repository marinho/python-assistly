# Python Assistly Wrapper

## Overview

Assistly.com is a web2.0 service for web support, offering functions like private and public cases,
interactions between clients and operators, many users, user groups, topics, etc.

Assistly offers an API following the REST best known concepts, under OAuth authentication and JSON
format.

python-assistly is a wrapper library to make easy and accessible to implement the Assistly API with
Python language.

## How to install

You can get the current trunk version from our git respository:

    git clone git@github.com:mochii/python-assistly.git
    cd python-assistly
    python setup.py install

### Coming soon

You will just do the same you usually do:

    pip install python-assistly

or

    easy_install python-assistly

or just download the tarball, uncompress and:

    python setup.py install

## Dependencies

python-assistly depends on the following packages to work properly:

- simplejson
- oauth2
- httplib2

Thanks to their authors.

## How to use it

You can read the test files to see how everything work.

The basic thing is:

    from assistly import AssistlyAPI
    api = AssistlyAPI(base_url='YOUR_ASSISTLY_SUBDOMAIN', key='YOUR_CONSUMER_EY', secret='YOUR_CONSUMER_SECRET')
    api.set_token(token_key='YOUR_TOKEN_KEY', token_secret='YOUR_TOKEN_SECRET')
    api.verify_credentials()
    response = api.interaction_create(subject='SUBJECT', customer_email='YOUR@EMAIL.COM')
    print response.interaction
    print response.case
    print response.customer

## API documentation

The official API documentation will inform you which arguments and fields are available:

http://dev.assistly.com/

Assistly's support can also help you:

http://support.assistly.com/

## Copyright

- python-assistly is under Mochii Ltd. rights, released as free software under the BSD license.
- Assistly is a trademark of Assistly Inc.
