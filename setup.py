""" setup.py - Script to install package using distutils

For help options run:
$ python setup.py help

"""
#Author: Ian Huston


from setuptools import setup
import re
import ast

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('getinspire/getinspire.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(f.read().decode('utf-8')).group(1)))


setup_args = dict(name='getinspire',
                  version=version,
                  author='Diego Restrepo',
                  author_email='diego.restrepo@gmail.com',
                  url='https://github.com/rescolo/getinspire',
                  packages=['getinspire'],
                  install_requires=[],
                  entry_points={
                      'console_scripts': 'getinspire = getinspire.getinspire:getinspire_main'
                  },
                  zip_safe=False,
                  license="Modified BSD license",
                  description="""getinspire queries the INSPIRE HEP database and returns to fill the bibtex o bibitem records of some LaTeX file """,
                  long_description=open('README.rst').read(),
                  classifiers=["Topic :: Utilities",
                               "Intended Audience :: Science/Research",
                               "License :: OSI Approved :: BSD License",
                               "Operating System :: OS Independent",
                               "Programming Language :: Python",
                               "Programming Language :: Python :: 2.6",
                               ],
                  )

if __name__ == "__main__":
    setup(**setup_args)
