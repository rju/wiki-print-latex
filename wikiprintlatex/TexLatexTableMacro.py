# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2007 Renato Chencarek <renato.chencarek@gmail.com>
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# Author: Renato Chencarek <renato.chencarek@gmail.com>

from trac.wiki.macros import WikiMacroBase

class TexLatexTableMacro(WikiMacroBase):
    r'''Include all necessary packages and macros to render latex tables.
    '''
    def expand_macro(self, formatter, name, content):
        return r'''\usepackage{tabularx}
\usepackage{booktabs}
\renewcommand{\tabularxcolumn}[1]{>{\arraybackslash}m{#1}}
\newcolumntype{K}{>{\flushleft\arraybackslash}X<{}}
\newcommand{\mytable}[3]{\begin{table}[!h]\begin{tabularx}{\textwidth}{#2}#1\end{tabularx}\end{table}}
'''

class TexLatexLongTableMacro(WikiMacroBase):
    r'''Include all necessary packages and macros to render latex tables.
    '''
    def expand_macro(self, formatter, name, content):
        return r'''\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{xtab}

\tabletail{\hline\hline}
\newlength{\colsize}
\newcolumntype{K}{>{\flushleft\arraybackslash}m{\colsize}}
\newcommand{\mytable}[3]{
\colsize=\the\textwidth
\divide\colsize by #3
\advance\colsize by -2.0\tabcolsep
\begin{xtabular}{#2}#1\end{xtabular}
}
'''
