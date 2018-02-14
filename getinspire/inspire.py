from __future__ import absolute_import, division, print_function, unicode_literals
import sys, re
from enum import Enum

if sys.version_info.major == 3:
    from urllib.parse import quote_plus, urlencode
    from urllib.request import urlopen, Request
    from html.parser import HTMLParser
else:
    from urllib import quote_plus, urlencode
    from urllib2 import urlopen, Request
    from HTMLParser import HTMLParser


class RecordNotFound(RuntimeWarning):
    def __init__(self, query):
        self.query = query

    def __str__(self):
        return 'texkey: {} not found in inspire'.format(self.query)


class MultipleRecordsFound(RuntimeWarning):
    def __init__(self, query, url):
        self.query = query
        self.url = url

    def __str__(self):
        return 'texkey: {} found more than one in inspire, {}'.format(self.query, self.url)


class SkipUnknownQuery(RuntimeWarning):
    def __init__(self, query):
        self.query = query

    def __str__(self):
        return 'texkey: {} is skipped because of unknown type'.format(self.query)


class InspireHTMLParser(HTMLParser):
    """
    Fetch <pre>...</pre> in <div class="pagebody"></div>
    """
    def __init__(self):
        HTMLParser.__init__(self)
        self.div_depth = 0
        self.div_pagebody = None
        self.pre_list = []
        self.pre_content = None

    def handle_starttag(self, tag, attr):
        if tag == 'div':
            self.div_depth += 1
            for name, value in attr:
                if name == 'class' and value == 'pagebody':
                    self.div_pagebody = self.div_depth
        elif tag == 'pre':
            if self.div_pagebody <= self.div_depth:
                self.pre_content = ""

    def handle_endtag(self, tag):
        if self.div_depth > 0 and tag == 'div':
            self.div_depth -= 1
            if self.div_pagebody is not None and self.div_pagebody > self.div_depth:
                self.div_pagebody = None
        elif tag == 'pre':
            if self.pre_content is not None:
                self.pre_list.append(self.pre_content)
            self.pre_content = None

    def handle_data(self, data):
        if self.pre_content is not None:
            self.pre_content += data + '\n'


class Key:
    class Type(Enum):
        UNKNOWN = 0
        INSPIRE = 1
        ARXIV = 2

    # Misho wondered if there is some rule for texkeys, but seems not: just random letters?
    # https://github.com/inspirehep/inspire-next/issues/613
    INSPIRE_REGEX = re.compile('^[a-z0-9\'.-]+:[0-9a-z]+$', re.IGNORECASE)  # do not use \w; '_' should be excluded
    ARXIV_REGEX = re.compile('^(?:arxiv:?)?(([a-z.-]+/\d{7})|(\d{4}\.\d{4,5}))$', re.IGNORECASE)

    @classmethod
    def format(cls, key):  # can I extend an Enum-based class??
        if cls.INSPIRE_REGEX.match(key):
            return key, cls.Type.INSPIRE
        match = cls.ARXIV_REGEX.match(key)
        if match:
            return match.group(1), cls.Type.ARXIV
        else:
            return key, cls.Type.UNKNOWN

    @classmethod
    def is_unknown(cls, key):
        return cls.format(key)[1] == cls.Type.UNKNOWN

    @classmethod
    def is_inspire(cls, key):
        return cls.format(key)[1] == cls.Type.INSPIRE

    @classmethod
    def is_arxiv(cls, key):
        return cls.format(key)[1] == cls.Type.ARXIV


class Inspire:
    API = 'https://inspirehep.net/search'
    LATEX_FORMAT = dict(US='elxu', EU='hlxe')

    @classmethod
    def fetch_latex(cls, key, output_type='EU'):
        return cls.fetch(key, cls.LATEX_FORMAT[output_type])

    @classmethod
    def fetch_bibtex(cls, key):
        return cls.fetch(key, 'hx')

    @classmethod
    def fetch(cls, key, output_format):
        (bare_key, key_type) = Key.format(key)
        if key_type == Key.Type.INSPIRE:
            query = bare_key
        elif key_type == Key.Type.ARXIV:
            query = 'find eprint {}'.format(bare_key)
        else:
            raise SkipUnknownQuery(key)

        params = dict(
            p=query,
            of=output_format,
            ln='en',
            rg=3,
        )
        query_url = cls.API + '?' + urlencode(params)

        # Not treat errors here; just raise as is.
        f = urlopen(query_url)  # "with" does not work on python2
        s = f.read()
        f.close()

        # Should we use BeautifulSoup?
        parser = InspireHTMLParser()
        parser.feed(s.decode("utf-8"))
        results = parser.pre_list

        if len(results) == 0:
            raise RecordNotFound(key)
        elif len(results) > 1:
            raise MultipleRecordsFound(key, query_url)
        else:
            return results[0].strip()
