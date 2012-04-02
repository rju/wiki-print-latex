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

from trac.core import *
import traceback
from trac.env import open_environment
from trac.mimeview.api import Context
from trac.wiki.parser import WikiParser
from trac.util import escape
from trac.mimeview.api import IContentConverter

from trac.mimeview import *
from trac.wiki.api import WikiSystem
from trac.util.html import escape, Markup, Element, html, plaintext
from trac.util.text import shorten_line, to_unicode

from trac.wiki.formatter import *
from trac.wiki.formatter import WikiProcessor

from tempfile import *
import glob, sys

from StringIO import StringIO

import os
import re

from trac.perm import IPermissionRequestor
from trac.web.chrome import ITemplateProvider, add_script, add_notice, add_warning
from trac.admin.web_ui import IAdminPanelProvider
from genshi.core import Markup
from api import IWikiPrintFormat
from trac.wiki.api import WikiSystem
from trac.web.api import RequestDone
import urllib
from trac.wiki.model import WikiPage


def system_message(msg, text=None):
    return os.linesep + text + os.linesep


class WikiPrintAdmin(Component):
    """A plugin allowing the export of multiple wiki pages in a single file."""
    formats = ExtensionPoint(IWikiPrintFormat)

    implements(IPermissionRequestor, IAdminPanelProvider, ITemplateProvider)

    # IPermissionRequestor methods
    def get_permission_actions(self):
        return ['WIKIPRINT_ADMIN', 'WIKIPRINT_FILESYSTEM', 'WIKIPRINT_BOOK']

    # ITemplateProvider methods
    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('wikiprint', resource_filename(__name__, 'htdocs'))]

    # IAdminPanelsProvider methods
    def get_admin_panels(self, req):
        if req.perm.has_permission('WIKIPRINT_ADMIN'):
            yield ('wikiprint', 'WikiPrint', 'options', 'Options')
        if req.perm.has_permission('WIKIPRINT_BOOK'):
            yield ('wikiprint', 'WikiPrint', 'makebook', 'Make Book')

    # IAdminPanelProvider methods
    def render_admin_panel(self, req, cat, page, component):

        if page == 'makebook':
            return self._render_book(req, cat, page, component)
        if page == 'options':
            return self._render_options(req, cat, page, component)

    def _render_book(self, req, cat, page, component):
        req.perm.assert_permission('WIKIPRINT_BOOK')
        data = {}

        allpages = list(WikiSystem(self.env).get_pages())
        rightpages = [x for x in req.session.get('wikiprint_rightpages', '').split(',') if x]
        """
        formats = {}
        for provider in self.formats:
            for format, name in provider.wikiprint_formats(req):
                formats[format] = {
                    'name': name,
                    'provider': provider,
                }
        """
        if req.method == 'POST' and req.args.get('create'):
            rightpages = req.args.get('rightpages_all')
            title = req.args.get('title') or self.env.project_name
            subject = req.args.get('subject')
            date = req.args.get('date')
            version = req.args.get('version')
            format = req.args.get('format')

            req.session['wikiprint_rightpages'] = rightpages
            rightpages = rightpages.split(',')

            #if not format or format not in formats:
            #    raise TracError('Bad format given for WikiPrint output.')

            pdfbookname = title.replace(' ', '_').replace(':', '_').replace(',', '_')
            # Start here
            test = self.formats
            return test[0].process_wikiprintlatex(req, format, title, subject, rightpages, version, date, pdfbookname)  
            #return formats[format]['provider'].process_wikiprint(req, format, title, subject, rightpages, version, date, pdfbookname)

        data['allpages'] = allpages
        leftpages = [x for x in allpages if x not in rightpages]
        leftpages.sort()
        data['leftpages'] = leftpages
        data['rightpages'] = rightpages
#        data['formats'] = formats
#        data['default_format'] = formats.iterkeys().next()

        add_script(req, 'wikiprint/js/admin_wikiprint.js')

        return 'admin_wikibook.html', data

    def _render_options(self, req, cat, page, component):
        req.perm.assert_permission('WIKIPRINT_ADMIN')
        data = {}

        if req.method == 'POST' and req.args.get('saveurls'):
            self.env.config.set('wikiprint', 'css_url', req.args.get('css_url'))
            self.env.config.set('wikiprint', 'article_css_url', req.args.get('article_css_url'))
            self.env.config.set('wikiprint', 'book_css_url', req.args.get('book_css_url'))
            self.env.config.set('wikiprint', 'frontpage_url', req.args.get('frontpage_url'))
            self.env.config.set('wikiprint', 'extracontent_url', req.args.get('extracontent_url'))
            add_notice(req, "URLs saved")
            self.env.config.save()
        elif req.method == 'POST' and req.args.get('savehttpauth'):
            self.env.config.set('wikiprint', 'httpauth_user', req.args.get('httpauth_user'))
            self.env.config.set('wikiprint', 'httpauth_password', req.args.get('httpauth_password'))
            add_notice(req, "User and password saved")
            self.env.config.save()
        elif req.method == 'POST' and req.args.get('viewcss'):
            self.env.log.debug("Wikiprint, Viewing CSS")
            return self._send_resource_file(req, 'text/css', req.args.get('css_url'), defaults.CSS)
        elif req.method == 'POST' and req.args.get('viewbookcss'):
            self.env.log.debug("Wikiprint, Viewing Book CSS")
            return self._send_resource_file(req, 'text/css', req.args.get('book_css_url'), defaults.BOOK_EXTRA_CSS)
        elif req.method == 'POST' and req.args.get('viewarticlecss'):
            self.env.log.debug("Wikiprint, Viewing Article CSS")
            return self._send_resource_file(req, 'text/css', req.args.get('article_css_url'), defaults.ARTICLE_EXTRA_CSS)
        elif req.method == 'POST' and req.args.get('viewfrontpage'):
            self.env.log.debug("Wikiprint, Viewing Front page")
            return self._send_resource_file(req, 'text/html', req.args.get('frontpage_url'), defaults.FRONTPAGE)
        elif req.method == 'POST' and req.args.get('viewextracontent'):
            self.env.log.debug("Wikiprint, Viewing Extra Contents")
            return self._send_resource_file(req, 'text/html', req.args.get('extracontent_url'), defaults.EXTRA_CONTENT)

        data['css_url'] = self.env.config.get('wikiprint', 'css_url')
        data['article_css_url'] = self.env.config.get('wikiprint', 'article_css_url')
        data['book_css_url'] = self.env.config.get('wikiprint', 'book_css_url')
        data['frontpage_url'] = self.env.config.get('wikiprint', 'frontpage_url')
        data['extracontent_url'] = self.env.config.get('wikiprint', 'extracontent_url')


        data['httpauth_user'] = self.env.config.get('wikiprint', 'httpauth_user')
        data['httpauth_password'] = self.env.config.get('wikiprint', 'httpauth_password')

        return 'admin_wikiprint.html', data

    def _send_resource_file(self, req, content_type, file, default_value):
        # Send the output
        req.send_response(200)
        req.send_header('Content-Type', 'text/plain')
        if not file:
            out = default_value
        else:
            linkloader = wikiprint.linkLoader(self.env, req, allow_local = True)
            resolved_file = linkloader.getFileName(file)
            if not resolved_file :
                raise Exception("File or URL load problem: %s (need WIKIPRINT_FILESYSTEM permissions?)" % file)
            try:
                f = open(resolved_file)
                out = f.read()
                f.close()
            except IOError:
                raise Exception("File or URL load problem: %s (IO Error)" % file)
            del linkloader

        req.send_header('Content-Length', len(out))
        req.end_headers()
        req.write(out)
        raise RequestDone


class WikiPrintOutput(Component):
    """Add output formats TEX to the WikiPrintLatex plugin."""
    implements(IWikiPrintFormat)
    
    def wikiprintlatex_formats(self, req):
        yield 'pdfarticle', 'PDF Article'
        yield 'pdfbook', 'PDF Book'
        yield 'printhtml', 'HTML'

    def process_wikiprintlatex(self, req, format, title, subject, pages, version, date, pdfname):

        # Send the output
        req.send_response(200)
        req.send_header('Content-Type', 'text/plain')

        context = Context.from_request(req, absurls=False)

        text = ""
        out = ""

        tempdir = mkdtemp(prefix="trac2latex")
        self.env.tempdir = tempdir
        codepage = self.env.config.get('trac', 'charset', 'ISO8859-15')

        for p in pages:
            text = WikiPage(self.env, p).text
            text = text.encode(codepage, 'ignore')
            temp = StringIO()
            TexFormatter(self.env, context).format(text, temp, False)
            out += temp.getvalue().encode(codepage)

        page = out.encode(codepage, 'ignore')

#        page = latex_article_header()
        page = out
#        page += latex_default_footer()


        req.send_header('Content-Length', len(out))
        req.end_headers()
        req.write(out)
        raise RequestDone

class TexFormatter(Formatter):

    def __init__(self, env, context, begindoc = False):
        Formatter.__init__(self, env, context)

        self.latex_rules = []
        self.latex_rules.append(r"(?P<latexescape>[&{}_=#%])")
        pattern = self.wikiparser.rules.pattern
        n = len(pattern)
        p1 = "|".join(self.latex_rules)
        p2 = pattern[3:][:-1]
        self.pattern = '(?:' + p2 + "|" + p1 + ')'

        self.my_rules = re.compile(self.pattern)
        self.open_tags = []
        self.list_depth = 0

        self.absurls = False
        self.begindoc = begindoc
        self.enddoc = False

    def _bolditalic_formatter(self, match, fullmatch):
        italic = ('\emph{', '}')
        italic_open = self.tag_open_p(italic)
        tmp = ''
        if italic_open:
            tmp += italic[1]
            self.close_tag(italic[1])
        tmp += self._bold_formatter(match, fullmatch)
        if not italic_open:
            tmp += italic[0]
            self.open_tag(*italic)
        return tmp

    def _bold_formatter(self, match, fullmatch):
        return self.simple_tag_handler(match, r'\textbf{', '}')

    def _italic_formatter(self, match, fullmatch):
        return self.simple_tag_handler(match, r'\emph{', '}')

    def _underline_formatter(self, match, fullmatch):
        return self.simple_tag_handler(match, r'\underline{','}')

    def _strike_formatter(self, match, fullmatch):
        return self.simple_tag_handler(match, r'\sout{', '}')

    def _subscript_formatter(self, match, fullmatch):
        return self.simple_tag_handler(match, r'$_{', '}$')

    def _superscript_formatter(self, match, fullmatch):
        return self.simple_tag_handler(match, r'$^{', '}$')

    def _inlinecode_formatter(self, match, fullmatch):
        return self.escape_verb(fullmatch.group('inline'))

    def _inlinecode2_formatter(self, match, fullmatch):
        return self.escape_verb(fullmatch.group('inline2'))

    # LATEX and HTML escape of &, < and >

    def escape_verb(self, match):
        sep = "|"
        for p in "|!^*$@":
            if p not in match:
                sep = p
                break

        result = self._latexescape_formatter(match, None)
        return result

    def _latexescape_formatter(self, match, fullmatch):
        for c in "><=":
            if c in match:
                match = match.replace('%s' % c,"$%s$" % c)
        for c in "&{}_#%":
            if c in match:
                match = match.replace('%s' % c,"\\%s" % c)

        return match

    def _latexescape_comments(self, match, fullmatch):
        match = match.replace('%', "\\%")
        return match

    def _htmlescape_formatter(self, match, fullmatch):
        return self._latexescape_formatter( match, fullmatch)

    # Links

    def wpl_format_link(self, formatter, ns, page, label, ignore_missing):
        page, query, fragment = formatter.split_link(page)
        href = formatter.href.wiki(page) + fragment
        return self.escape_verb(label)

    def _lhref_formatter(self, match, fullmatch):
        rel = fullmatch.group('rel')
        ns = fullmatch.group('lns')
        target = self._unquote(fullmatch.group('ltgt'))
        label = fullmatch.group('label')
        if not label: # e.g. `[http://target]` or `[wiki:target]`
            if target:
                if target.startswith('//'): # for `[http://target]`
                    label = ns+':'+target   #  use `http://target`
                else:                       # for `wiki:target`
                    return self.escape_verb(target) #  use only `target`
            else: # e.g. `[search:]`
                return ""
        else:
            label = self._unquote(label)
        if rel:
            return self._make_relative_link(rel, label or rel)
        else:
            return self.wpl_make_link(ns, target, match, label)

    def wpl_make_link(self, ns, target, match, label):
        # first check for an alias defined in trac.ini
        ns = self.env.config.get('intertrac', ns) or ns

        if ns in self.wikiparser.link_resolvers:
            if not '#' in target:
                return self.escape_verb(label)
            return  self._make_relative_link(target.split('#')[1], label)
        elif target.startswith('//') or ns == "mailto":
            return self._make_ext_link(ns+':'+target, label)
        else:
            return self._make_intertrac_link(ns, target, label) or \
                   self._make_interwiki_link(ns, target, label) or \
                   match

    def _make_interwiki_link(self, ns, target, label):
        from trac.wiki.interwiki import InterWikiMap
        interwiki = InterWikiMap(self.env)
        if ns in interwiki:
            url, title = interwiki.url(ns, target)
            return self._make_ext_link(url, label, title)
        else:
            return None

        ns = self.env.config.get('intertrac', ns) or ns

        if ns in self.wikiparser.link_resolvers:
            if not '#' in target:
                return self.escape_verb(label)
            return  self._make_relative_link(target.split('#')[1], label)
        elif target.startswith('//') or ns == "mailto":
            return self._make_ext_link(ns+':'+target, label)
        else:
            return self._make_intertrac_link(ns, target, label) or \
                   self._make_interwiki_link(ns, target, label) or \
                   match

    def _make_ext_link(self, url, text, title=''):
        text = self._latexescape_comments(text, None)
        url = self._latexescape_comments(url, None)
        if text == url:
            return r"\url{%s}" % url
        else:
            return r"\href{%s}{%s}" % (url, text)

    def _make_relative_link(self, url, text):
        text = self._latexescape_comments(text, None)
        url = self._latexescape_comments(url, None)
        if text == url:
            return r"\url{%s}" % url
        else:
            return r"\hyperref[%s]{%s}" % (url.lstrip("#"), text)


    # Headings

    def _parse_heading(self, match, fullmatch, shorten):
        match = match.strip()

        depth = min(len(fullmatch.group('hdepth')), 5)
        anchor = fullmatch.group('hanchor') or ''
        heading_text = match[depth+1:-depth-1-len(anchor)]
        heading = wiki_to_oneliner(self.env, heading_text, self.db, False,
                                   self.absurls)
        if anchor:
            anchor = anchor[1:]
        else:
            sans_markup = plaintext(heading, keeplinebreaks=False)
            anchor = WikiParser._anchor_re.sub('', sans_markup)
            if not anchor or anchor[0].isdigit() or anchor[0] in '.-':
                # an ID must start with a Name-start character in XHTML
                anchor = 'a' + anchor # keeping 'a' for backward compat
        i = 1
        anchor_base = anchor
        while anchor in self._anchors:
            anchor = anchor_base + str(i)
            i += 1
        self._anchors[anchor] = True
        if shorten:
            heading = wiki_to_oneliner(self.env, heading_text, self.db, True,
                                       self.absurls)
        return (depth, heading, anchor)

    def _heading_formatter(self, match, fullmatch):
        self.wpl_close_table()
        self.close_paragraph()
        self.close_indentation()
        self.close_list()
        self.close_def_list()
        depth, heading, anchor = self._parse_heading(match, fullmatch, False)

        self.out.write(os.linesep + ('\%ssection{%s}\n\label{%s}\n' % ("sub" * (depth - 1), heading, anchor)) + os.linesep)

    # Generic indentation (as defined by lists and quotes)

    def _set_tab(self, depth):
        """Append a new tab if needed and truncate tabs deeper than `depth`

        given:       -*-----*--*---*--
        setting:              *
        results in:  -*-----*-*-------
        """
        tabstops = []
        for ts in self._tabstops:
            if ts >= depth:
                break
            tabstops.append(ts)
        tabstops.append(depth)
        self._tabstops = tabstops

    # Paragraphs

    def open_paragraph(self):
        if not self.paragraph_open:
            self.out.write(os.linesep)

            self.paragraph_open = 1

    def close_paragraph(self):
        if self.paragraph_open:
            while self._open_tags != []:
                self.out.write(self._open_tags.pop()[1])
            self.paragraph_open = 0

    # Definition Lists

    def _definition_formatter(self, match, fullmatch):
        if self.in_def_list:
            tmp = ""
        else:
            tmp = r'\begin{description}' + os.linesep + os.linesep

        definition = match[:match.find('::')]
        tmp += r'\item{%s}' % wiki_to_oneliner(self.env, definition, self.db)
        self.in_def_list = True
        return tmp

    def close_def_list(self):
        if self.in_def_list:
            self.out.write( os.linesep + r'\end{description}' + os.linesep)
        self.in_def_list = False

    # Blockquote

    def _set_quote_depth(self, depth, citation=False):
        def open_quote(depth):
            self.wpl_close_table()
            self.close_paragraph()
            self.close_list()
            def open_one_quote(d):
                self._quote_stack.append(d)
                self._set_tab(d)
                class_attr = citation and ' class="citation"' or ''
            if citation:
                for d in range(quote_depth+1, depth+1):
                    open_one_quote(d)
            else:
                open_one_quote(depth)
        def close_quote():
            self.wpl_close_table()
            self.close_paragraph()
            self._quote_stack.pop()

        quote_depth = self._get_quote_depth()
        if depth > quote_depth:
            self._set_tab(depth)
            tabstops = self._tabstops[::-1]
            while tabstops:
                tab = tabstops.pop()
                if tab > quote_depth:
                    open_quote(tab)
        else:
            while self._quote_stack:
                deepest_offset = self._quote_stack[-1]
                if depth >= deepest_offset:
                    break
                close_quote()
            if not citation and depth > 0:
                if self._quote_stack:
                    old_offset = self._quote_stack[-1]
                    if old_offset != depth: # adjust last depth
                        self._quote_stack[-1] = depth
                else:
                    open_quote(depth)
        if depth > 0:
            self.in_quote = True

    # Table

    def _last_table_cell_formatter(self, match, fullmatch):
        return ''

    def _table_cell_formatter(self, match, fullmatch):
        self.wpl_open_table()
        self.wpl_open_table_row()
        self.current_cols += 1
        if self.current_cols > self.max_cols:
            self.max_cols = self.current_cols
        if self.in_table_cell:
            return ' & '
        else:
            self.in_table_cell = 1
            return ''

    def wpl_open_table(self):
        if not self.in_table:
            self.close_paragraph()
            self.close_list()
            self.close_def_list()
            self.in_table = 1
            self.max_cols = 0
            self.out.write(os.linesep + r'\mytable{%' + os.linesep)

    def wpl_open_table_row(self):
        if not self.in_table_row:
            self.wpl_open_table()
            self.in_table_row = 1
            self.current_cols = 0
            self.out.write(r'\hline' + os.linesep )

    def wpl_close_table_row(self):
        if self.in_table_row:
            self.in_table_row = 0
            self.in_table_cell = 0
            if self.current_cols > self.max_cols:
                self.max_cols = self.current_cols
            self.out.write(r"\tabularnewline")

    def wpl_close_table(self):
        if self.in_table:
            self.wpl_close_table_row()
            self.out.write(r'\hline' + os.linesep)
            self.out.write(r'}{|%s}{%d}' % ("K|" * self.max_cols, self.max_cols) + os.linesep)
            self.in_table = 0

    # Lists

    def _list_formatter(self, match, fullmatch):
        ldepth = len(fullmatch.group('ldepth'))
        listid = match[ldepth]
        self.in_list_item = True
        class_ = start = None
        if listid in '-*':
            type_ = 'ul'
        else:
            type_ = 'ol'
            idx = '01iI'.find(listid)
            if idx >= 0:
                class_ = ('arabiczero', None, 'lowerroman', 'upperroman')[idx]
            elif listid.isdigit():
                start = match[ldepth:match.find('.')]
            elif listid.islower():
                class_ = 'loweralpha'
            elif listid.isupper():
                class_ = 'upperalpha'
        self._set_list_depth(ldepth, type_, class_, start)
        return ''

    def _get_list_depth(self):
        """Return the space offset associated to the deepest opened list."""
        return self._list_stack and self._list_stack[-1][1] or 0

    def _set_list_depth(self, depth, new_type, list_class, start):
        def open_list():
            self.wpl_close_table()
            self.close_paragraph()
            self.close_indentation() # FIXME: why not lists in quotes?
            self._list_stack.append((new_type, depth))
            self._set_tab(depth)
            class_attr = list_class and ' class="%s"' % list_class or ''
            start_attr = start and ' start="%s"' % start or ''
            self.out.write (r'\begin{itemize}' + os.linesep)

            self.list_depth += 1
            self.out.write('\\item ')

        def close_list(tp):
            self._list_stack.pop()
            self.out.write (r'\end{itemize}' + os.linesep)

            self.list_depth -= 1

        # depending on the indent/dedent, open or close lists
        if depth > self._get_list_depth():
            open_list()
        else:
            while self._list_stack:
                deepest_type, deepest_offset = self._list_stack[-1]
                if depth >= deepest_offset:
                    break
                close_list(deepest_type)
            if depth > 0:
                if self._list_stack:
                    old_type, old_offset = self._list_stack[-1]
                    if new_type and old_type != new_type:
                        close_list(old_type)
                        open_list()
                    else:
                        if old_offset != depth: # adjust last depth
                            self._list_stack[-1] = (old_type, depth)
                        self.out.write('\\item ')
                else:
                    open_list()

    def close_list(self):
        self._set_list_depth(0, None, None, None)

    # Code blocks

    def handle_code_block(self, line):
        if line.strip() == WikiParser.STARTBLOCK:
            self.in_code_block += 1
            if self.in_code_block == 1:
                self.code_processor = None
                self.code_text = ''
            else:
                self.code_text += line + os.linesep
        elif line.strip() == WikiParser.ENDBLOCK:
            self.in_code_block -= 1
            if self.in_code_block == 0:
                self.wpl_close_table()
                self.close_paragraph()
                if self.code_processor:
                    language = self.code_processor
                    if language == "Latex":
                        if  self.code_text.startswith(WikiParser.STARTBLOCK):
                            self.out.write(r'\begin{verbatim}' + os.linesep + self.code_text + os.linesep + r'\end{verbatim}')
                        else:
                            self.out.write(self.code_text)
                    else:
                        body = r'\begin{lstlisting}' + os.linesep + self.code_text + os.linesep + r'\end{lstlisting}'
                        self.out.write(r'''
\lstset{language=%s,
frame=single,
showstringspaces=false,
extendedchars=true,
backgroundcolor=\color[rgb]{0.95,0.95,0.95},
rulecolor=\color[rgb]{0.3,0.3,0.3},
basicstyle=\small\upshape\ttfamily,
commentstyle=\color[rgb]{0.5,0.0,0.0}\rmfamily\itshape,
keywordstyle=\color[rgb]{0.7,0.0,0.8}\bfseries,
stringstyle=\color[rgb]{0.6,0.4,0.4},
identifierstyle=\color[rgb]{0.2,0.2,0.9}
}''' % language + os.linesep + body + os.linesep)
                else:
                    self.out.write(r'\begin{verbatim}' + os.linesep + self.code_text + os.linesep + r'\end{verbatim}')
            else:
                self.code_text += line + os.linesep
        elif not self.code_processor:
            match = WikiParser._processor_re.search(line)
            if match:
                name = match.group(1)
                self.code_processor = name
            else:
                self.code_text += line + os.linesep
                self.code_processor = None
        else:
            self.code_text += line + os.linesep

    def close_code_blocks(self):
        while self.in_code_block > 0:
            self.handle_code_block(WikiParser.ENDBLOCK)

    # WikiMacros

    def wpl_macro_formatter(self, match, fullmatch):
        name = fullmatch.group('macroname')
        if name.lower() == 'latexdoccls':
            self.begindoc = True
        if name.lower() == 'latexenddoc':
            self.enddoc = True

        if name.lower() == 'br':
            return os.linesep + r'\\' + os.linesep

        name = 'Tex' + name
        args = fullmatch.group('macroargs')
        try:
            macro = WikiProcessor(self, name)
            return macro.process(args, True)
        except Exception, e:
            self.env.log.error('Macro %s(%s) failed' % (name, args), exc_info=True)
            return None #system_message("Macro %s not found" % name)

    # -- Wiki engine

    def handle_match(self, fullmatch):
        for itype, match in fullmatch.groupdict().items():
            if match and not itype in self.wikiparser.helper_patterns:
                # Check for preceding escape character '!'
                if match[0] == '!':
                    return self.escape_verb(escape(match[1:]))
                if itype in self.wikiparser.external_handlers:
                    if itype in ["i0", "i1", "i2"]:
                        return match

                    external_handler = self.wikiparser.external_handlers["i0"]

#Hier liegt der Hund begraben.    

#                    tmp = self.wiki._format_link
#                    self.wiki._format_link = self.wpl_format_link
                    ret =  external_handler(self, match, fullmatch)
#                    self.wiki._format_link = tmp
                    return ret
                else:
                    internal_handler = getattr(self, '_%s_formatter' % itype)
                    return internal_handler(match, fullmatch)


    def format(self, text, out=None, escape_newlines=False):
        if not text:
            return
        self.reset(text, out)

        for line in text.splitlines():
            # Handle code block
            if self.in_code_block or line.strip() == WikiParser.STARTBLOCK:
                self.handle_code_block(line)
                continue
            # Handle Horizontal ruler
            elif line[0:4] == '----':
                self.wpl_close_table()
                self.close_paragraph()
                self.close_indentation()
                self.close_list()
                self.close_def_list()
                self.out.write(os.linesep + r'\rule{\textwidth}{1pt}' + os.linesep)
                continue
            # Handle new paragraph
            elif line == '':
                self.close_paragraph()
                self.close_indentation()
                self.close_list()
                self.close_def_list()
                continue

            # Tab expansion and clear tabstops if no indent
            line = line.replace('\t', ' '*8)
            if not line.startswith(' '):
                self._tabstops = []

            if escape_newlines:
                line += r' \\'
            self.in_list_item = False
            self.in_quote = False
            # Throw a bunch of regexps on the problem

            result = re.sub(self.my_rules, self.replace, line)

            if not self.in_list_item:
                self.close_list()

            if not self.in_quote:
                self.close_indentation()

            if self.in_def_list and not line.startswith(' '):
                self.close_def_list()

            if self.in_table and line.strip()[0:2] != '||':
                self.wpl_close_table()

            if len(result) and not self.in_list_item and not self.in_def_list \
                    and not self.in_table:
                self.open_paragraph()

            self.out.write(result + os.linesep)

            self.wpl_close_table_row()

            if self.enddoc:
                self.enddoc = True
                self.begindoc = False

        self.wpl_close_table()
        self.close_paragraph()
        self.close_indentation()
        self.close_list()
        self.close_def_list()
        self.close_code_blocks()

class OneLinerTexFormatter(TexFormatter):
    """
    A special version of the wiki formatter that only implement a
    subset of the wiki formatting functions. This version is useful
    for rendering short wiki-formatted messages on a single line
    """
    flavor = 'oneliner'

    def __init__(self, env, context):
        TexFormatter.__init__(self, env, context)

    def wpl_macro_formatter(self, match, fullmatch):
        name = fullmatch.group('macroname')
        if name.lower() == 'br':
            return os.linesep
        elif name == 'comment':
            return '%'
        else:
            args = fullmatch.group('macroargs')
            return '[[%s%s]]' % (name,  args and '(...)' or '')

    def format(self, text, out, shorten=False):
        if not text:
            return
        self.out = out
        self._open_tags = []

        # Simplify code blocks
        in_code_block = 0
        processor = None
        buf = StringIO()
        for line in text.strip().splitlines():
            if line.strip() == WikiParser.STARTBLOCK:
                in_code_block += 1
            elif line.strip() == WikiParser.ENDBLOCK:
                if in_code_block:
                    in_code_block -= 1
                    if in_code_block == 0:
                        if processor != 'comment':
                            buf.write(' ![...]' + os.linesep)
                        processor = None
            elif in_code_block:
                if not processor:
                    if line.startswith('#!'):
                        processor = line[2:].strip()
            else:
                buf.write(line + os.linesep)
        result = buf.getvalue()[:-1]

        if shorten:
            result = shorten_line(result)

        result = re.sub(self.my_rules, self.replace, result)

        result = result.replace('[...]', '[&hellip;]')
        if result.endswith('...'):
            result = result[:-3] + '&hellip;'

        # Close all open 'one line'-tags
        result += self.close_tag(None)
        # Flush unterminated code blocks
        if in_code_block > 0:
            result += '[&hellip;]'
        out.write(result)

def wiki_to_oneliner(env, wikitext, db=None, shorten=False, absurls=False, req=None):
    if not wikitext:
        return Markup()
    out = StringIO()
    context = Context.from_request(req, absurls=False)
    OneLinerTexFormatter(env, context).format(wikitext, out, shorten)
    return Markup(out.getvalue())

def latex_default_header():
    return ""

def latex_default_end():
    return ""

class Trac2LATEXPlugin(Component):
    """Convert Wiki pages to LATEX using HTML2LATEX"""
    implements(IContentConverter)

    def clean_tmp_dir(self, tempdir):
        for f in glob.glob(os.path.join(tempdir ,"*")):
            os.unlink(f)
        os.rmdir(tempdir)

    def read_log(self, tempdir):
        fin = open(tempdir + "/log", "r")
        page = fin.read()
        fin.close()
        return page

    # IContentConverter methods
    def get_supported_conversions(self):
        yield ('tex', 'Latex', 'tex', 'text/x-trac-wiki', 'application/tex', 7)
        yield ('pdf', 'Latex-Pdf', 'pdf', 'text/x-trac-wiki', 'application/x-pdf', 7)

    def convert_content(self, req, input_type, source, output_type):
        try:
            self.env.log.debug('Trac2LATEX starting')

            context = Context.from_request(req, absurls=False)

            tempdir = mkdtemp(prefix="trac2latex")
            self.env.tempdir = tempdir
            codepage = self.env.config.get('trac', 'charset', 'ISO8859-15')
            page = source.encode(codepage, 'ignore')

            out = StringIO()
	    
            f = TexFormatter(self.env, context).format(source, out, False)

            page = latex_default_header()
            page += out.getvalue().encode(codepage)
            page += latex_default_end()

            if "tex" in output_type:
                self.clean_tmp_dir(tempdir)
                return (page, 'application/tex')

            try:
                fd, tmpfile = mkstemp(dir=tempdir, prefix='trac2latex')
                fout = open(tmpfile + ".tex", "w")
                fout.write(page)
                fout.close()
            except Exception, e:
                print "ERROR: Cannot create temporary file %s" % (tmpfile + ".tex")
                return ("ERROR: Cannot create temporary file %s" % (tmpfile + ".tex"), 'text/html')

            try:
                curdir = os.getcwd()
                os.chdir(tempdir)
                os.system("pdflatex -interaction=nonstopmode " + tmpfile + ".tex > " + tempdir + "/log")
                os.system("bibtex " + tmpfile + "  >> " + tempdir + "/log")
                os.system("pdflatex -interaction=nonstopmode " + tmpfile + ".tex >> " + tempdir + "/log")
                os.system("pdflatex -interaction=nonstopmode " + tmpfile + ".tex >> " + tempdir + "/log")
                os.chdir(curdir)
                fin = open(tmpfile + ".pdf", "r")
                page = fin.read()
                fin.close()
            except Exception, e:
                error = "LATEX PARSER ERROR: %s" % traceback.extract_tb(sys.exc_info()[2])
                print error
                return (error, 'text/html')

            self.clean_tmp_dir(tempdir)

            return (page, 'application/x-pdf')

        except Exception, e:
            error = "LATEX PARSER ERROR: %s" % traceback.extract_tb(sys.exc_info()[2])
            print error
            return (error, 'text/html')



from trac.wiki.macros import WikiMacroBase

class TexIncludeMacro(WikiMacroBase):
    """
    This is the Tex version of Image macro.
    """
    def expand_macro(self, formatter, name, content):
        db = self.env.get_db_cnx()

        txt = content or ''
        args = txt.split('|')
        url = args.pop(0).replace("'", "''")

        if ":" in url:
            base, name = url.split(":")
            if base != "wiki":
                return "Use 'wiki:' prefix in wiki page url", base, name
        else:
            name = url

        sql = "SELECT text from wiki where name = '%s' order by version desc limit 1" % name
        cs = db.cursor()
        cs.execute(sql)
        result = cs.fetchone()

        if not result:
            return '<b>Wiki Page %s not found!</b>' % url

        text = result[0]
        out = StringIO()
        TexFormatter(formatter.env, formatter.context, True).format(text, out, False)
        text = out.getvalue()

        return text

