import os
import re

__version__ = re.search("__version__\s*=\s*'(.*)'", open('assistly/__init__.py').read(), re.M).group(1)
assert __version__
__author__ = re.search("__author__\s*=\s*'(.*)'", open('assistly/__init__.py').read(), re.M).group(1)
assert __author__
__license__ = re.search("__license__\s*=\s*'(.*)'", open('assistly/__init__.py').read(), re.M).group(1)
assert __license__

# Downloads setuptools if not find it before try to import
try:
    import ez_setup
    ez_setup.use_setuptools()
except ImportError:
    pass

from setuptools import setup

def fullsplit(path, result=None):
    """
    Split a pathname into components (the opposite of os.path.join) in a
    platform-neutral way. Copied from Django.
    """
    if result is None:
        result = []
    head, tail = os.path.split(path)
    if head == '':
        return [tail] + result
    if head == path:
        return result
    return fullsplit(head, [tail] + result)

packages = []
data_files = []
assistly_dir = 'assistly'

for dirpath, dirnames, filenames in os.walk(assistly_dir):
    for i, dirname in enumerate(dirnames):
        if dirname.startswith('.'): del dirnames[i]

    if '__init__.py' in filenames:
        packages.append('.'.join(fullsplit(dirpath)))

    elif filenames:
        data_files.append([dirpath, [os.path.join(dirpath, f) for f in filenames]])    

setup(
    name='python-assistly',
    version=__version__,
    #url='',
    author=__author__,
    license=__license__,
    packages=packages,
    data_files=data_files,
    install_requires=['distribute','simplejson==2.2.1','oauth2==1.5.170','httplib2==0.7.1'],
    setup_requires=['httplib2==0.7.1'],
    )
