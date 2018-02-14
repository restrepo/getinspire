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
        return 'texkey: {} not found in inspire\n'.format(self.query)


class MultipleRecordsFound(RuntimeWarning):
    def __init__(self, query, url):
        self.query = query
        self.url = url

    def __str__(self):
        return 'texkey: {} found more than one in inspire, {}'.format(self.query, self.url)


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
        OTHER = 0
        INSPIRE = 1
        ARXIV = 2

    # Misho wondered if there is some rule for texkeys, but seems not: just random letters?
    # https://github.com/inspirehep/inspire-next/issues/613
    INSPIRE_REGEX = re.compile('^[a-z0-9\'.-]+:[0-9a-z]+$', re.IGNORECASE)  # do not use \w; '_' should be excluded
    ARXIV_REGEX = re.compile('^(?:arxiv:?)?(([a-z.-]+/\d{7})|(\d{4}\.\d{4,5}))$', re.IGNORECASE)

    @classmethod
    def format(cls, key):  # can I extend an Enum-based class??
        print(key)
        if cls.INSPIRE_REGEX.match(key):
            return key, cls.Type.INSPIRE
        match = cls.ARXIV_REGEX.match(key)
        if match:
            return match.group(1), cls.Type.ARXIV
        else:
            return key, cls.Type.OTHER


class Inspire:
    API = 'https://inspirehep.net/search'

    @classmethod
    def bibtex(cls, key):
        return cls.search(cls.get_query(key), 'hx')

    @classmethod
    def latex_us(cls, key):
        return cls.search(cls.get_query(key), 'hlxu')

    @classmethod
    def latex_eu(cls, key):
        return cls.search(cls.get_query(key), 'hlxe')

    @classmethod
    def get_query(cls, raw_key):
        (key, key_type) = Key.format(raw_key)
        if key_type == Key.Type.INSPIRE:
            return key
        elif key_type == Key.Type.ARXIV:
            return 'find eprint {}'.format(key)
        else:
            return None

    @classmethod
    def search(cls, raw_query, output_type):
        if raw_query is None:
            return None

        params = dict(
            p=raw_query,
            of=output_type,
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
            raise RecordNotFound(raw_query)
        elif len(results) > 1:
            raise MultipleRecordsFound(raw_query, query_url)
        else:
            return results[0]


# if __name__ == '__main__':
#     print(Inspire.bibtex('arxiv:1303.4256'))
