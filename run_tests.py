import os
import sys
import assistly
from nose.core import TestProgram

def main():
    tests_dir = os.path.join(os.path.dirname(assistly.__path__[0]), 'tests')
    sys.path.insert(0, tests_dir)

    argv = ['nosetests','--with-doctest','--doctest-extension=txt','--verbosity=2','--where='+tests_dir]
    program = TestProgram(argv=argv, exit=False)

if __name__ == '__main__':
    main()

