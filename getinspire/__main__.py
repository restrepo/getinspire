import os
import sys

"""
Entry point if executed as 'python getinspire
"""


if __name__ == '__main__':
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), os.pardir)
    sys.path.insert(0, path)
    from getinspire.getinspire import getinspire_main
    sys.exit(getinspire_main())
