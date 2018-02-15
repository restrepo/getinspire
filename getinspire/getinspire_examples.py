def sample_bibtex():
    return r"""\documentclass{article}
%uncommet if you like collect references
%\usepackage{collref}
%\collectsep{;\ }

\begin{document}
\section{Introduction}
The Inter Dark Matter model was first proposed
in~\cite{Deshpande:1977rw}. Later, after the electroweak precision
data excluded the possibility of a heavy standard model Higgs, it was
found that this simplest extension may accommodate Higgs masses of
several hundreds of GeV's~\cite{hep-ph/0603188}. Yet this possibility
is ruled out by the discovery of a new boson by ATLAS~\cite{1207.7214}
and CMS~\cite{1207.7235}, the model have Dark Matter regions compatible
with a $125\ $GeV standard model
Higgs~\cite{hep-ph/0612275,0903.4010,0911.0540}


\bibliographystyle{h-physrev4} 
\bibliography{idm}

\end{document}
    """

def sample_latex():
    return r"""\documentclass{article}
%uncommet if you like collect references
%\usepackage{collref}
%\collectsep{;\ }

\begin{document}
\section{Introduction}
The Inter Dark Matter model was first proposed
in~\cite{Deshpande:1977rw}. Later, after the electroweak precision
data excluded the possibility of a heavy standard model Higgs, it was
found that this simplest extension may accommodate Higgs masses of
several hundreds of GeV's~\cite{hep-ph/0603188}. Yet this possibility
is ruled out by the discovery of a new boson by ATLAS~\cite{1207.7214}
and CMS~\cite{1207.7235}, the model have Dark Matter regions compatible
with a $125\ $GeV standard model
Higgs~\cite{hep-ph/0612275,0903.4010,0911.0540}

\input{sample_latex.bbl}

\end{document}
    """
