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
from collections import OrderedDict
from enum import Enum
import time
import re
import sys
import os.path
import optparse

from inspire import Inspire, Key
from getinspire_examples import sample_latex, sample_bibtex

import pybtex.database

__version__ = "0.2.0"

class FileNotFoundError(IOError):
    def __init__(self, errors=None, paths=None):
        self.paths = paths
        if __debug__:
            [print(e) for e in errors]

    def __str__(self):
        return "File not found in search paths " + self.paths.__str__()


class MultipleBibError(NotImplementedError):
    def __init__(self):
        pass

    def __str__(self):
        return "currently cannot handle TeX with multiple bib files."


class TeX:
    CITE_REGEX = re.compile(r'(\\cite(\[.*?\])?{(.*?)})', re.DOTALL)
    CITE_BIB_IN_TEX = re.compile(r'\\bibliography{(.*?)}', re.DOTALL)
    CITE_BIB_IN_AUX = re.compile(r'\\bibdata{(.*?)}', re.DOTALL)

    def __init__(self, filename):
        errors = []
        possible_paths = [filename, filename + '.tex'];
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
        if errors:
            raise FileNotFoundError(errors=errors, paths=possible_paths)
        self._bib_name = None
        self._bib = None

    def cite_commands(self):
        return [match[0] for match in self.CITE_REGEX.findall(self.text)]

    def references(self):
        # Note that the order is very important!
        refs = OrderedDict()
        for cite in self.CITE_REGEX.finditer(self.text):
            for key in re.split(r'\s*,\s*', cite.group(3)):
                if key not in refs:
                    refs[key] = Ref(key)
        return refs

    def aux_name(self):
        return self.stem + '.aux'

    def bbl_name(self):
        return self.stem + '.bbl'

    def bib_name(self):
        if self._bib_name is None:
            aux_data = self.get_aux()
            bib_keys = self.CITE_BIB_IN_TEX.findall(self.text) if aux_data is None \
                       else self.CITE_BIB_IN_AUX.findall(aux_data)
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

    def get_aux(self):
        try:
            with open(self.aux_name(), mode='r') as file:
                aux_data = file.read()
        except IOError:
            aux_data = None
        return aux_data

    def bib(self):
        if self._bib is None:
            self._bib = pybtex.database.parse_file(self.bib_name(), bib_format='bibtex') if self.bib_name() else False
        return self._bib


texkeyregex=r'[a-zA-Z\'\.\-]*:[0-9a-z]*'
eptkregex=r'[a-zA-Z:0-9,\/\-._\']*'
def checkfind(s):
    find={}
    if re.search(r'[0-9]{4}\.[0-9]{4}',s) or re.search(r'[a-z\-\/]*[0-9]{7}',s):
        find['eprint']=s
    elif re.search(texkeyregex,s):
        find['texkey']=s
    else:
        find['other']=s
        
    return find
        
def inspirehtml(value,formath):
    s=''
    finddict=checkfind(value)
    if finddict.has_key('eprint'):
        find='eprint'
    elif finddict.has_key('texkey'):
        find='texkey'
    else:
        find='other'
        #sys.exit('&find=%s  no yet implemented')

        
    searchurl=r'http://inspirehep.net/search?ln=es&p=find+%s+%s&of=%s'\
               %(find,value,formath)
    f = urllib2.urlopen(searchurl)
    # Read from the object, storing the page's contents in 's'.
    s = f.read()
    f.close()
    if re.search('403 Forbidden',s)>0:
        sys.exit('Blocked by inspire: 403 Forbidden')
    #get the <pre> tag contents:
    if re.search('<pre>',s)>0:
        s=s.split('<pre>')[1].split('</pre>')[0]
        #del extra newlines
        s=re.sub('^\n','',s)
        s=re.sub('^\n','',s)
        if formath=='hlxe' or formath=='hlxu':
            s=re.sub(r'^%.*\n','',s.replace('<br>','\n').replace('&nbsp;',' '))
    else:
        s='NotFound'
        
    return s


class Record:
    """
    Representation of a single, specific particle, decay block from an SLHA
    file.  These objects are not themselves called 'Decay', since that concept
    applies more naturally to the various decays found inside this
    object. Particle classes store the PDG ID (pid) of the particle being
    represented, and optionally the mass (mass) and total decay width
    (totalwidth) of that particle in the SLHA scenario. Masses may also be found
    via the MASS block, from which the Particle.mass property is filled, if at
    all. They also store a list of Decay objects (decays) which are probably the
    item of most interest.
    """
    def __init__(self,*args, **keyargs):
        self.eprint = {}
        self.texkey = {}

    def getBibTeX(self,search='Komine:2000tj'):
        Bibtexkey='';Bibeprint=''
        formath='hx'
        BibTeX=inspirehtml(search,'hx')
            
        #get texkey value
        if re.search(r'@[A-Za-z]+{(.*),',BibTeX):
            Bibtexkey=re.search(r'@[A-Za-z]+{(.*),',BibTeX).groups()[0]
            
        #get eprint value
        if re.search('eprint\s*=(.*),',BibTeX):
            Bibeprint=re.sub('\s*"','',re.search('eprint\s*=(.*),',BibTeX).groups()[0])
        if Bibtexkey and Bibeprint:
            self.texkey[Bibeprint]=Bibtexkey
            self.eprint[Bibtexkey]=Bibeprint

        return BibTeX

    def getLaTeX(self,search='Komine:2000tj',lformat='EU'):
        formatdict={'EU':'hlxe','US':'hlxu'}
        return inspirehtml(search,formatdict[lformat])


#        def __cmp__(self, other):

#        def __str__(self):

#        def __repr__(self):


class Cite:
    """
    replace=pyinspire.Cite()
    replace('0949.2432','mundo:2012','\\cite{0949.2432}')
    """
    def __init__(self,*args, **keyargs):
        self.texkey = {}
        self.list=[]

    def __call__(self,eprint='0949.2432',texkey='mundo:2012',s=r'\\cite{0949.2432}'):
        return self.replace(eprint,texkey,s)

    def ExtractTexkeys(self,s):
        list=[re.sub(':::','',k).split(',') for  k in [j.group() for j in [re.search(':::(.*):::',i) for i in re.sub(r'\\cite{(%s)}' %eptkregex,'\n:::\\1:::\n',s).split('\n')] if j]]
        for i in list: 
            for j in i:
                if not self.texkey.has_key(j):
                    self.texkey[j]=''
                    self.list.append(j)
                    
        self.texkeylist=self.texkey.keys()
        
    def replace(self,eprint,texkey,s):
        s=re.sub(r'(\\cite{%s)%s(%s})' %(eptkregex,eprint,eptkregex),r'\1%s\2' %texkey,s)
        return s
    

def replaceeprint(eprint,texkey,s):
    s=re.sub(r'(\\cite{%s)%s(%s})' %(eptkregex,eprint,eptkregex),r'\1%s\2' %texkey,s)
    return s


def ExtractBibkeys(s):
    texkey={}
    list=[re.sub(':::','',j.group()) for j in [re.search(':::(.*):::',i) for i in re.sub(r'\@[A-Za-z]+{(%s),' %texkeyregex,r':::\1:::',s).split('\n')] if j]
    for i in list: 
        if not texkey.has_key(i):
                texkey[i]=''

    return texkey


def ExtractBibitemkeys(s):
    return [re.sub(':::','',j.group()) for j in [re.search(':::(.*):::',i) for i in re.sub(r'\\bibitem{(%s)}' %texkeyregex,r':::\1:::',s).split('\n')] if j]

def list2dict(l):
    d={}
    for i in l:
        d[i]=''
        
    return d
        
    
def replace_eprint2texkeys(Cite,s):

    bibentry=Record()
    for i in Cite.texkey.iterkeys():
        if checkfind(i).has_key('eprint'):
            bibentry.getBibTeX(i)
            time.sleep(0.2)
            sys.stdout.write('.')

    sys.stdout.write('\n')

    if len(bibentry.texkey)>0:
        for i in bibentry.texkey.iterkeys():
            #replace eprint by texkeys in LaTeX file
            s=replaceeprint(i,bibentry.texkey[i],s)
            print 'Replacing %s by %s in LaTeX file' %(i,bibentry.texkey[i])

    return s

def insert_BibTeXRecord_to_bib_file(Cite,bibfile):
    """
    Automatically insert inspire BibTeX records to the bib file
    """
    if not os.path.exists(bibfile):
        f=open(bibfile,'w')
        f.write('')
        f.close()
        
    f=open(bibfile) 
    art=f.read()
    f.close()

    f=open(bibfile,'a') #preparing to append to bib file
    #Extract BibTeX Keys from bib file (as dictionary):
    bibtexfile_keys=ExtractBibkeys(art)

    newbib=Record()
    
    sys.stdout.write('Downloading newbibs\n')

    for i in Cite.texkey.iterkeys():
        if checkfind(i).has_key('texkey'):
            if not bibtexfile_keys.has_key(i):
                bib=newbib.getBibTeX(i)
                time.sleep(0.2)
                sys.stdout.write('.')
                if bib!='NotFound':
                    f.write(bib)
                    print 'Get BibTeX Record for %s from inspire' %i
                else:
                    sys.stdout.write('WARNING: texkey: %s not found in inspire\n' %i)


    sys.stdout.write('\n')
    f.close()

def replace_bblfile_format_with_inspireLaTeX(bblfile,bbltoinspire,lformat='EU'): #or 'US'
    """
     If you don't like the format generated for the bst file you can use this
     function to change to inspire LaTeX(EU/US) bibitem format.

     It is recommended to use for the final document.
    """
    newbib=Record()
    if os.path.exists(bblfile) and bbltoinspire:
        f=open(bblfile)
        bbl=f.read()
        f.close()
        bibitemlist=ExtractBibitemkeys(bbl)
        f=open(bblfile,'w')
        f.write('\\begin{thebibliography}{10}\n\n')
        for i in bibitemlist:
            bib=newbib.getLaTeX(i,lformat)
            time.sleep(0.2)
            print '.',
            if bib!='NotFound':
                f.write(bib)
                f.write('\n')
                print 'Get LaTeX(%s) Record for %s from inspire' %(lformat,i)
            else:
                sys.stdout.write('WARNING: texkey: %s not found in inspire\n' %i)

        f.write('\end{thebibliography}\n')
        f.close()
        #check bbl file
        f=open(bblfile)
        bbl=f.read()
        f.close()
        bibitemlistnew=ExtractBibitemkeys(bbl)
        if len(bibitemlist)==len(bibitemlistnew):
            print('\n%s successfully generated' %bblfile)
        else:
            print('\nWrong %s generation. Rerun bibtex fo fix it' %bblfile)
    else:
        print('run bibtex and/or set --bbl option \n to obtain bbl file in inspire format')        

def get_bblfile_from_inspireLaTeX_records(Cite,bblfile,lformat='EU',append=False): #or 'US'
    """File to be insterded/replaced in the bibliography of LaTeX file.
       If append=False the new records are appended to the end of the file
       and the sequence of the references os not keeped.
       If append=True all the bibitems are download in sequential order from
       spires and the references are automatically ordered in the LaTeX file.

       It is recommended to use append=False during the draft process, and switch to True
       for the final document.
    """
    bbl=''
    if os.path.exists(bblfile) and append:
        f=open(bblfile)
        bbl=f.read()
        f.close()
        bbl=re.sub(r'\\end{thebibliography}','',bbl)
        
    f=open(bblfile,'w')
    f.write(bbl)
    f.close()
        
    bibitemlist=ExtractBibitemkeys(bbl)
    bibitemdict=list2dict(bibitemlist)

    newbib=Record()
    f=open(bblfile,'a')
    if not append:
        f.write('\\begin{thebibliography}{10}\n\n')
        
    for i in Cite.list:
        if append and bibitemdict.has_key(i):
            sys.stdout.write('.')
        else:    
            bib=newbib.getLaTeX(i,lformat)
            time.sleep(0.2)
            print '.',
            if bib!='NotFound':
                f.write(bib)
                f.write('\n')
                print 'Get LaTeX(%s) Record for %s from inspire' %(lformat,i)
            else:
                sys.stdout.write('WARNING: texkey: %s not found in inspire\n' %i)

    f.write('\end{thebibliography}\n')
    f.close()
    print('Insert %s generated file in your LaTeX file' %bblfile)


def getinspire_main():
    #********** COMMAND LINE ARGUMENTS
    latexformat='EU'
    appendbli=False
    if len(sys.argv)==1:
        print "%s --help" %sys.argv[0]
        sys.exit()
        
    #Parse command line options
    usage = "%prog [options] file.tex\n"+__doc__
    parser = optparse.OptionParser(usage=usage, version=__version__)
            
    parser.add_option("-t", "--thebibliography", action="store_true", dest="thebibliography", 
                      help="Not BibTeX mode: Create bbl file with sequential \\begin{thebibliography} \\bibitems records")
    parser.add_option("-a", "--thebibliographyappend", action="store_true", dest="thebibliographyappend", 
                      help="Not BibTeX mode: add \\bibitems to bbl file ")

    parser.add_option("-b", "--bbl", action="store_true", dest="bbltoinspire", 
                      help="Replace BibTeX generated file with bbl file in inspire format")

    parser.add_option("--LaTeXUS", action="store_const", 
                      dest="format", const="US",
                  help="LaTeX(US) Format of bibitem recors (Default: LaTeX(EU)")
    parser.add_option("--sample_bibtex", action="store_true", dest="show_sample_bibtex", 
                      help="Show sample LaTeX file with BibTeX, and exit")      
    parser.add_option("--sample_latex", action="store_true", dest="show_sample_latex", 
                      help=r"Show sample LaTeX file with \begin{thebibliography} mode, and exit")      
    (options, args) = parser.parse_args()

    if options.show_sample_bibtex:
        print sample_bibtex()
        sys.exit()

    if options.show_sample_latex:
        print sample_latex()
        sys.exit()
        
    if options.format:
        latexformat=options.format
        
    if len(args)==0 or len(args)>1:
        print "%s --help" %sys.argv[0]
        sys.exit()
        
    latexfile=args[-1]
    if re.search('\.tex',latexfile):
        bblfile=re.sub('\.tex','.bbl',latexfile)
    else:
        bblfile='%s.bbl' %latexfile
        latexfile='%s.tex' %latexfile

    if not os.path.exists(latexfile):
        print 'ERROR: No such file: %s' %latexfile
        sys.exit()
        
    thebibliography=options.thebibliography
    if options.thebibliographyappend:
        thebibliography=True
        appendbli=True
        
    bbltoinspire=options.bbltoinspire
    
    f=open(latexfile)
    s=f.read()
    f.close()

    if not thebibliography:
        uns=s+'\n'
        uns=re.sub('%(.*)\n','\n',uns) #drop comments
        if re.search(r'\\bibliography{(.*)}',uns):
            bibfile=re.search(r'\\bibliography{(.*)}',uns).groups()[0]
            if not re.search('\.bib',bibfile):
                bibfile=bibfile+'.bib'

        else:
            print """ERROR: LaTeX File not seem to be using bibtex.
            Use -t option for \\begin{thebibliography} style
            or set \\bibliography command in LaTeX file
            """
            sys.exit()

        if not os.path.exists(bibfile):
            print 'WARNING: bibtex file: %s, will be created' %bibfile

    #*********************************
    
    #Extract cite keys from LaTeX file (as list)
    cites=Cite()
    cites.ExtractTexkeys(s)

    #====replace eprints by texkeys============
    news=replace_eprint2texkeys(cites,s)
    #write latexfile
    if news!=s:
        f=open(latexfile,'w')
        f.write(news)
        f.close()
        #Add new texkey to cites object
        cites.ExtractTexkeys(news)
        
    #******** thebibliography mode *****************
    if thebibliography:
        #Just generate a bbl file to include in the LaTeX file
        get_bblfile_from_inspireLaTeX_records(cites,bblfile,lformat=latexformat,append=appendbli)
        sys.exit()
    #*********************************************

    #******** bibtex mode **************************
    #======Add BibTeX records to file.bib
    insert_BibTeXRecord_to_bib_file(cites,bibfile)
    #========================================
    #=== Replace bbl file with inspire LaTeX(EU/US) format
    replace_bblfile_format_with_inspireLaTeX(bblfile,bbltoinspire,lformat=latexformat)
    #=======================================
    #******************************************

if __name__ == '__main__':
    exit(getinspire_main())
