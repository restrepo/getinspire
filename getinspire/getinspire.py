#!/usr/bin/env python
'''
Get inspire (http://inspirehep.net) records to fill the bibliography of a LaTeX file

BibTeX is assumed as the default format of the LaTeX file.
The bib file name is obtained from the LaTeX file. The
missing BibTeX records are obtained from inspire and appended
to the bib file.

The program requires the \cite key in the "texkey" format
of inspire (LastName:yearCODE). However if a \cite has an
eprint number as key, like hep-ph/0213456 or 1206:0001, it will
be automatically converted to a "texkey". Then both the LaTeX
file and the bib file will be updated.

The BibTeX bbl generated file can be changed by one with The
LaTeX records with the inspire format (see --bbl option)

The \\begin{thebibliography} format can be also processed with
the output in an external bbl file (see -t option)

Examples:
 $ getinspire sample_bibtex.tex
 $ getinspire -t sample_latexeu.tex
'''

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys
import re
import optparse
import time
from functools import total_ordering

from inspire import *
from getinspire_examples import sample_latex, sample_bibtex

import pybtex.database
from pybtex.utils import OrderedCaseInsensitiveDict as ODict

__version__ = "0.2.0"
DEBUG = False


class FileLookupFailedError(IOError):
    def __init__(self, errors=None, paths=None):
        self.paths = paths
        if DEBUG:
            [print(e) for e in errors]

    def __str__(self):
        return "File not found in search paths " + self.paths.__str__()


class ReplacementError(RuntimeError):
    def __init__(self, line, column, old, new, actual):
        self.msg = "L{} C{} from {} to {} but actually {}".format(line, column, old, new, actual)

    def __str__(self):
        return "LaTeX file replacement failed: " + self.msg


class MultipleBibError(NotImplementedError):
    def __init__(self):
        pass

    def __str__(self):
        return "currently cannot handle TeX with multiple bib files."


class InvalidFetchResult(NotImplementedError):
    def __init__(self, result):
        self.result = result
        pass

    def __str__(self):
        return "InspireHEP returns unexpected data:\n\n" + self.result


@total_ordering
class Position(object):
    LINESEP_REGEX = re.compile(r'\r\n|\r|\n')
    LASTLINE_REGEX = re.compile(r'.*$')

    """
    The position of the caret after `str`.
    Line `l` and column `c` are both zero-origin, so
    Position('abc') gives (0,3) while Position('a\nb\n') gives (2,0).
    """

    def __init__(self, **kwargs):
        if 'str' in kwargs:
            self.l = len(self.LINESEP_REGEX.findall(kwargs['str']))
            self.c = len(self.LASTLINE_REGEX.search(kwargs['str']).group(0))
        elif 'l' in kwargs and 'c' in kwargs:
            self.l = kwargs['l']
            self.c = kwargs['c']
        else:
            RuntimeError('Invalid initialization of Position')

    def __str__(self):
        return '(L{} C{})'.format(self.l, self.c)

    def shift(self, string):
        other = Position(str=string)
        if other.l == 0:
            self.c += other.c
        else:
            self.l += other.l
            self.c = other.c
        return self

    def __eq__(self, other):
        return self.l == other.l and self.c == other.c

    def __lt__(self, other):
        if self.l == other.l:
            return self.c.__lt__(other.c)
        else:
            return self.l.__lt__(other.l)

    def copy(self):
        return Position(l=self.l, c=self.c)


class TeX(object):
    CITE_REGEX = re.compile(r'(?P<pre>(\\cite(\[.*?\])?{))(?P<body>.*?)}', re.DOTALL)
    CITE_BIB_IN_TEX = re.compile(r'\\bibliography{(.*?)}', re.DOTALL)
    CITE_BIB_IN_BBL = re.compile(r'\\bibitem{(.*?)}', re.DOTALL)
    COMMENTS_REGEX = re.compile(r'((?:^|[^\\])(?:\\\\)*)%.*$', re.MULTILINE)

    @classmethod
    def strip_comment(cls, string):
        return cls.COMMENTS_REGEX.sub(r'\1', string)

    def __init__(self, filename):
        self.text = None
        errors = []
        possible_paths = [filename, filename + '.tex']
        for path in possible_paths:
            try:
                with open(path, mode='r') as file:
                    self.text_original = file.read()
                    self.text = self.text_original
                    self.filename = path
                    self.stem = os.path.splitext(path)[0]
                    break
            except IOError as e:
                errors.append(e)
                pass
        if self.text is None:
            raise FileLookupFailedError(errors=errors, paths=possible_paths)

        self._bib_name = None
        self._bib = None
        self._bbl = None

        # generate references
        text_uncommented = self.strip_comment(self.text)
        self.references = ODict()  # Order is important!
        for cite in self.CITE_REGEX.finditer(text_uncommented):
            pos = Position(str=text_uncommented[:cite.start()])
            pos.shift(cite.group('pre'))
            for key_raw in re.split(r',', cite.group('body')):
                stripping = re.match(r'^(\s*)(\S+)(\s*)$', key_raw)
                pos.shift(stripping.group(1))
                key = stripping.group(2)
                if key not in self.references:
                    self.references[key] = Ref(key, position=pos.copy())
                else:
                    self.references[key].positions.append(pos.copy())
                pos.shift(stripping.group(2)).shift(stripping.group(3))
                pos.shift(',')

    def write_tex(self):
        with open(self.filename, mode='w') as file:
            file.write(self.text)

    def bbl_name(self):
        return self.stem + '.bbl'

    def bbl(self):
        if self._bbl is None:
            if self.bbl_name() and os.path.exists(self.bbl_name()):
                try:
                    with open(self.bbl_name(), mode='r') as file:
                        self._bbl = file.read()
                except:
                    pass
            self._bbl = self._bbl or ""
        return self._bbl

    def modify_and_write_bbl(self, new_content, append=True):
        begin = '\\begin[10]{thebibliography}'
        end = '\\end{thebibliography}'
        if append:
            sep = re.split(r'\\end\s*{\s*thebibliography\s*}', self.bbl(), maxsplit=1)
            (bbl, footer) = sep if len(sep) == 2 else (sep[0], "")
            self._bbl = '\n'.join([bbl, new_content, end + footer])
        else:
            self._bbl = '\n\n'.join([begin, new_content, end])

        with open(self.bbl_name(), mode='w') as file:
            file.write(self.bbl())

    def bib_name(self):
        if self._bib_name is None:
            bib_keys = self.CITE_BIB_IN_TEX.findall(self.strip_comment(self.text))
            stem = None
            for bib_key in bib_keys:
                for bib in re.split(r'\s*,\s*', bib_key):
                    if stem is None:
                        stem = bib
                    elif stem != bib:
                        raise MultipleBibError
            if stem is None:
                self._bib_name = False  # for "not found"
            else:
                self._bib_name = os.path.join(os.path.dirname(self.filename), stem + '.bib')
        return self._bib_name

    def bib(self):
        if self._bib is None:
            if self.bib_name() and os.path.exists(self.bib_name()):
                try:
                    self._bib = pybtex.database.parse_file(self.bib_name(), bib_format='bibtex')
                except:
                    pass
            self._bib = self._bib or pybtex.database.BibliographyData()
        return self._bib

    # pybtex output are a bit buggy and avoided.
    # def append_bib(self, entries):
    #     # self._bib.add_entries(entries)  # maybe buggy?
    #     for k in entries.order:
    #         self._bib.add_entry(k, entries[k])
    # def update_bib(self):
    #     if self.bib_name():
    #         self._bib.to_file(self.bib_name(), bib_format='bibtex')
    #     else:
    #         raise RuntimeError()

    def append_and_update_bib(self, new_text):
        with open(self.bib_name(), mode='a') as file:
            file.write('\n' + new_text + '\n')
        self._bib = None  # clear and to be reload

    def bbl_keys(self):
        try:
            with open(self.bbl_name(), mode='r') as file:
                return self.CITE_BIB_IN_BBL.findall(self.strip_comment(file.read()))
        except IOError:
            return []

    def fetch_and_update(self, bibtex=True, latex_format='EU', append_bbl=False):
        existing_keys = self.bib().entries.keys() if bibtex else self.bbl_keys()
        existing_keys = [k.lower() for k in existing_keys]

        replace_keys = ODict()
        new_entries = ODict()
        type_name = 'BibTeX' if bibtex else 'LaTeX({})'.format(latex_format)

        for ref in self.references.values():
            if ref.key.lower() in existing_keys:
                if DEBUG:
                    print('skip existing: {}'.format(ref.key))
                continue
            if Key.is_unknown(ref.key):
                if DEBUG:
                    print('skip unknown: {}'.format(ref.key))
                continue

            try:
                print('fetching', type_name, 'from inspire:', ref.key, end=' ')
                if bibtex:
                    ref.fetch_bibtex()
                else:
                    ref.fetch_latex(latex_format)
                sys.stdout.flush()
                time.sleep(0.3)
            except RecordNotFound or MultipleRecordsFound as e:
                print('\nERROR: {}'.format(e))
                continue

            if ref.new_key:
                replace_keys[ref.old_key] = ref
                print('->', ref.new_key, end=' ')
                sys.stdout.flush()
                time.sleep(0.3)
            if ref.key.lower() not in existing_keys:
                existing_keys.append(ref.key.lower())
                new_entries[ref.key] = ref
                print('[new entry]', end='')
            print('')

        replacements = list()
        for ref in replace_keys.values():
            for appearance in ref.positions:
                replacements.append((appearance, ref.old_key, ref.new_key))
        self.replace_text(replacements)
        self.write_tex()

        new_ref_contents = '\n'.join(r.content for r in new_entries.values())
        if bibtex:
            self.append_and_update_bib(new_ref_contents)
        else:
            self.modify_and_write_bbl(new_ref_contents, append_bbl)

    def replace_text(self, replacement_rules):
        # replace from the end to the beginning not to break the positions
        replacement_rules = sorted(replacement_rules, key=lambda x: x[0], reverse=True)
        lines = Position.LINESEP_REGEX.split(self.text)
        for pos, old, new in replacement_rules:
            if lines[pos.l][pos.c:pos.c + len(old)] == old:
                lines[pos.l] = lines[pos.l][:pos.c] + new + lines[pos.l][pos.c + len(old):]
            else:
                raise ReplacementError(pos.l, pos.c, old, new, lines[pos.l][pos.c:pos.c + len(old)])
        self.text = '\n'.join(lines)


class Ref:
    def __init__(self, key, position=None):
        self.key = key
        self.old_key = key
        self.new_key = None
        self.positions = None if position is None else [position]
        self.content = None

    def fetch_latex(self, output_format='EU'):
        try:
            self.content = Inspire.fetch_latex(self.key, output_format)
        except SkipUnknownQuery as e:
            print(e)
            return
        # validation or messaging is done in TeX class
        match = re.search(r'\\bibitem{(.*?)}', self.content)
        if not match:
            raise InvalidFetchResult(self.content)
        new_key = match.group(1)
        if self.key != new_key:
            self.new_key = self.key = new_key

    def fetch_bibtex(self):
        try:
            self.content = Inspire.fetch_bibtex(self.key)
        except SkipUnknownQuery as e:
            print(e)
            return
        # validation or messaging is done in TeX class
        match = re.search(r'^@[a-zA-Z]+{(.*?),', self.content)
        if not match:
            raise InvalidFetchResult(self.content)
        new_key = match.group(1)
        if self.key != new_key:
            self.new_key = self.key = new_key


def getinspire_main():
    usage = "%prog [options] file.tex\n" + __doc__
    parser = optparse.OptionParser(usage=usage, version=__version__)

    parser.add_option("-t", "--thebibliography", action="store_true", dest="thebibliography",
                      help="Not BibTeX mode: Create bbl file with sequential \\begin{thebibliography} \\bibitems records")
    parser.add_option("-a", "--thebibliographyappend", action="store_true", dest="thebibliographyappend",
                      help="Not BibTeX mode: add \\bibitems to bbl file ")

    parser.add_option("--LaTeXUS", action="store_const",
                      dest="format", const="US",
                      help="LaTeX(US) Format of bibitem records (Default: LaTeX(EU)")
    parser.add_option("--sample_bibtex", action="store_true", dest="show_sample_bibtex",
                      help="Show sample LaTeX file with BibTeX, and exit")
    parser.add_option("--sample_latex", action="store_true", dest="show_sample_latex",
                      help=r"Show sample LaTeX file with \begin{thebibliography} mode, and exit")
    (options, args) = parser.parse_args()

    if len(args) != 1:
        print("%s --help" % sys.argv[0])
        sys.exit(1)

    if options.show_sample_bibtex:
        print(sample_bibtex())
        sys.exit(0)
    elif options.show_sample_latex:
        print(sample_latex())
        sys.exit(0)

    # command line options
    latex_format = options.format if options.format else 'EU'
    thebibliography = options.thebibliography
    append_bbl = False
    if options.thebibliographyappend:
        thebibliography = True
        append_bbl = True

    tex = TeX(args[-1])

    if thebibliography:  # non-BibTeX mode
        if tex.bib_name():
            print('WARNING: LaTeX file seem to be using BibTeX.')
            if not append_bbl and os.path.exists(tex.bbl_name()):
                print('If you want to overwrite the current bblfile, remove it and run again.')
            sys.exit(1)

        if append_bbl and not os.path.exists(tex.bbl_name()):
            print('WARNING: bbl file {} does not exist. You will manually include \\begin{thebibliography} etc.')
        elif not append_bbl and os.path.exists(tex.bbl_name()):
            print('ERROR: bbl file {} already exists; remove it before execute with -t option.')
            sys.exit(1)

        tex.fetch_and_update(bibtex=False, latex_format=latex_format, append_bbl=append_bbl)
        sys.exit(0)

    else:  # BibTeX mode
        if not tex.bib_name():  # if bib command not found
            print("""ERROR: LaTeX File not seem to be using bibtex.
            Use -t option for \\begin{thebibliography} style
            or set \\bibliography command in LaTeX file
            """)
            sys.exit(1)
        if not os.path.exists(tex.bib_name()):
            print('WARNING: bibtex file: {} will be created'.format(tex.bib_name()))

        tex.fetch_and_update(bibtex=True)
        sys.exit(0)


if __name__ == '__main__':
    exit(getinspire_main())
