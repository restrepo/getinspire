=================================================

GetInspire: Fill the bibliography of a LaTeX file

in BibTeX format

=================================================

This program get the \\cite texkeys in inspire.net format, e.g 'Author:2012aa', from your LaTeX file, download the corresponding BibTeX entry from inspire.net and update your BibTeX file. If the \\cite is in the arXiv fomat, e.g 1203.0978, the entry is first replaced by the texkey in inspire.net format inside your LaTeX file.

INSTALL 

$ sudo python setup.py install

(Requires the python-setuptools package: 
$ sudo apt-get install python-setuptools)

BASIC USAGE: 

$ getinspire latexfile.tex

see: 

$ getinspire --help

for a detailed help
