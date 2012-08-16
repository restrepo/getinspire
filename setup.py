""" setup.py - Script to install package using distutils

For help options run:
$ python setup.py help

"""
#Author: Ian Huston


from setuptools import setup

###############
VERSION = "0.1.0"


setup_args = dict(name='getinspire',
                  version=VERSION,
                  author='Diego Restrepo',
                  author_email='diego.restrepo@gmail.com',
                  url='https://github.com/rescolo/getinspire',
                  packages=['getinspire'],
                  scripts=['getinspire/getinspire'],
                  package_data={},
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
