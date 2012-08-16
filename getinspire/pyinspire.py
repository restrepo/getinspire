#!/usr/bin/env python
'''
Modules to interact with inspire (http://inspirehep.net)
'''
import urllib
import time
import re
import sys

__version__ = "0.1.0"

#__call__ example
class A:
    '''
    >>> a = A()
        initIn
    >>> a()
        call
    '''
    def __init__(self):
        print("init")
    def __call__(self):
        print("call")
def checkfind(s):
    find={}
    if re.search(r'[0-9]{4}\.[0-9]{4}',s) or re.search(r'[a-z\-\/]*[0-9]{7}',s):
        find['eprint']=s
    elif re.search('[A-Z][a-zA-Z]*:[0-9a-z]*',s):
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
        
    searchurl=r'http://inspirehep.net/search?ln=es&p=find+%s+%s&of=%s'\
               %(find,value,formath)
    f = urllib.urlopen(searchurl)
    # Read from the object, storing the page's contents in 's'.
    s = f.read()
    f.close()
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
        if re.search(r'@article{(.*),',BibTeX):
            Bibtexkey=re.search(r'@article{(.*),',BibTeX).groups()[0]
            
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
        list=[re.sub(':::','',k).split(',') for  k in [j.group() for j in [re.search(':::(.*):::',i) for i in re.sub(r'\\cite{([a-zA-Z:0-9,\/\-._]*)}','\n:::\\1:::\n',s).split('\n')] if j]]
        for i in list: 
            for j in i:
                if not self.texkey.has_key(j):
                    self.texkey[j]=''
                    self.list.append(j)
                    
        self.texkeylist=self.texkey.keys()
        
    def replace(self,eprint,texkey,s):
        s=re.sub(r'(\\cite{[a-zA-Z:0-9,\/\-._]*)%s([a-zA-Z:0-9,\/\-._]*})' %eprint,r'\1%s\2' %texkey,s)
        return s
    

