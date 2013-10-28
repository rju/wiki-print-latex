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
# Modified by: Gregor Hoops <grh@informatik.uni-kiel.de>

from trac.core import *
import traceback
from trac.env import open_environment
from trac.mimeview.api import Context
from trac.wiki.parser import WikiParser
from trac.util import escape

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
from trac.wiki.api import WikiSystem
from trac.web.api import RequestDone
import urllib
from trac.wiki.model import WikiPage

import mimetypes

class WikiPrintAdmin(Component):
    """A plugin allowing the export of multiple wiki pages in a single file."""
    implements(IPermissionRequestor, IAdminPanelProvider, ITemplateProvider)

    # IPermissionRequestor methods
    def get_permission_actions(self):
        return ['WIKIPRINTLATEX_ADMIN', 'WIKIPRINTLATEX_FILESYSTEM', 'WIKIPRINTLATEX_BOOK']

    # ITemplateProvider methods
    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('wikiprint', resource_filename(__name__, 'htdocs'))]

    # IAdminPanelsProvider methods
    def get_admin_panels(self, req):
        if req.perm.has_permission('WIKIPRINTLATEX_ADMIN'):
            yield ('wikiprintlatex', 'WikiPrintLatex', 'options', 'Options')
        if req.perm.has_permission('WIKIPRINTLATEX_BOOK'):
            yield ('wikiprintlatex', 'WikiPrintLatex', 'makebook', 'Make Book')

    def render_admin_panel(self, req, cat, page, component):

        if page == 'makebook':
            return self._render_book(req, cat, page, component)
        if page == 'options':
            return self._render_options(req, cat, page, component)

    def _render_book(self, req, cat, page, component):
        req.perm.assert_permission('WIKIPRINTLATEX_BOOK')
        data = {}

        allpages = list(WikiSystem(self.env).get_pages())
        rightpages = [x for x in req.session.get('wikiprint_rightpages', '').split(',') if x]
        
        if req.method == 'POST' and req.args.get('create'):
            rightpages = req.args.get('rightpages_all')
            title = req.args.get('title') or self.env.project_name
            subject = req.args.get('subject')
            date = req.args.get('date')
            version = req.args.get('version')

            req.session['wikiprint_rightpages'] = rightpages
            rightpages = rightpages.split(',')

            pdfbookname = title.replace(' ', '_').replace(':', '_').replace(',', '_')
            return self.process_wikiprintlatex(req, title, subject, rightpages, version, date, pdfbookname)  

        data['allpages'] = allpages
        leftpages = [x for x in allpages if x not in rightpages]
        leftpages.sort()
        data['leftpages'] = leftpages
        data['rightpages'] = rightpages

        add_script(req, 'wikiprint/js/admin_wikiprintlatex.js')

        return 'admin_makebook.html', data

    def _render_options(self, req, cat, page, component):
        req.perm.assert_permission('WIKIPRINTLATEX_ADMIN')
        data = {}
        
        if req.method == 'POST' and req.args.get('upload'):
            if req.args.get('uploadtemplate') != '': 
                up = req.args.get('uploadtemplate')
                option = 'template_url'
            elif req.args.get('uploadmacro') != '':
                up = req.args.get('uploadmacro')
                option = 'macro_url' 
            elif req.args.get('uploadlogo') != '':
                up = req.args.get('uploadlogo')
                option = 'logo_url' 
            elif req.args.get('uploadadditional') != '':
                up = req.args.get('uploadadditional')
                option = 'additional_url'
            else:
                raise TracError, 'Something went wrong'
 
            if not up.filename:
                raise TracError, 'No file uploaded'
            up_filename = up.filename.replace('\\', '/').replace(' ', '_').replace(':', '/')
            up_filename = os.path.basename(up_filename)
            if not up_filename:
                raise TracError, 'No file uploaded'
            
            targetpath = os.path.join(self.env.path, 'files', up_filename)
            content = up.file.read()
            tar = open(targetpath, 'w')
            tar.write(content)
            tar.close()

            self.env.config.set('wikiprintlatex', option, targetpath) 
        elif req.method == 'POST' and req.args.get('saveurls'):
            self.env.config.set('wikiprintlatex', 'macro_url', req.args.get('latex_macro_url'))
            self.env.config.set('wikiprintlatex', 'logo_url', req.args.get('latex_logo_url'))
            self.env.config.set('wikiprintlatex', 'additional_url', req.args.get('latex_additional_url'))
            self.env.config.set('wikiprintlatex', 'template_url', req.args.get('latex_template_url'))
            add_notice(req, "URLs saved")
            self.env.config.save()
        elif req.method == 'POST' and req.args.get('savehttpauth'):
            self.env.config.set('wikiprintlatex', 'httpauth_user', req.args.get('httpauth_user'))
            self.env.config.set('wikiprintlatex', 'httpauth_password', req.args.get('httpauth_password'))
            add_notice(req, "User and password saved")
            self.env.config.save()
        elif req.method == 'POST' and req.args.get('viewlatexmacro'):
            self.env.log.debug("Wikiprintlatex, Viewing Latex Macro")
            return self._send_resource_file(req, req.args.get('latex_macro_url'), 'No Latex macro file set...')
        elif req.method == 'POST' and req.args.get('viewlatexlogo'):
            self.env.log.debug("Wikiprintlatex, Viewing Logo")
            return self._send_resource_file(req, req.args.get('latex_logo_url'), 'No Logo file set...')
        elif req.method == 'POST' and req.args.get('viewlatexadditional'):
            self.env.log.debug("Wikiprintlatex, Viewing additional file")
            return self._send_resource_file(req, req.args.get('latex_additional_url'), 'No additional file set...')
        elif req.method == 'POST' and req.args.get('viewlatextemplate'):
            self.env.log.debug("Wikiprintlatex, Viewing Latex Template")
            return self._send_resource_file(req, req.args.get('latex_template_url'), 'No Latex template file set...')
 
        data['latex_macro_url'] = self.env.config.get('wikiprintlatex', 'macro_url')
        data['latex_logo_url'] = self.env.config.get('wikiprintlatex', 'logo_url')
        data['latex_additional_url'] = self.env.config.get('wikiprintlatex', 'additional_url')
        data['latex_template_url'] = self.env.config.get('wikiprintlatex', 'template_url')

        data['httpauth_user'] = self.env.config.get('wikiprintlatex', 'httpauth_user')
        data['httpauth_password'] = self.env.config.get('wikiprintlatex', 'httpauth_password')

        return 'admin_wikiprintlatex.html', data

    def _send_resource_file(self, req, file, default_value):
        # Send the output
        req.send_response(200)
        if not file:
            req.send_header('Content-Type', 'text/plain') 
            out = default_value
        else:
            try:
                f = open(file) 
                out = f.read()
                f.close()
                type = mimetypes.guess_type(file)
                if type[0] != None: 
                    req.send_header('Content-Type', type[0])
                else: 
                    req.send_header('Content-Type', 'text/plain')
            except IOError:
                raise Exception("File or URL load problem: %s " % file)

        req.send_header('Content-Length', len(out))
        req.end_headers()
        req.write(out)
        raise RequestDone

    def umlaut2latex(self, text):
        ret = text.replace(u'ö', u'\"o').replace(u'Ö', u'\"O').replace(u'ä', u'\"a').replace(u'Ä', u'\"A')
        ret = ret.replace(u'ü', u'\"u').replace(u'Ü', u'\"U').replace(u'ß', u'{\ss}')
        return ret

    def umlaut2plain(self, text):
        ret = text.replace(u'ö', u'oe').replace(u'Ö', u'Oe').replace(u'ä', u'ae').replace(u'Ä', u'Ae')
        ret = ret.replace(u'ü', u'ue').replace(u'Ü', u'Ue').replace(u'ß', u'ss')
        return ret

    def process_wikiprintlatex(self, req, title, subject, pages, version, date, pdfname):

        # Send the output
        req.send_response(200)
        req.send_header('Content-Type', 'text/plain')

        context = Context.from_request(req, absurls=False)

        tempdir = mkdtemp(prefix="wikiprintlatex") 
        self.env.tempdir = tempdir
        codepage = self.env.config.get('trac', 'charset', 'ISO8859-15')

        tardir = r"%s_%s" % (date, title) 
        tardir = tardir.replace(" ", "_").replace("/", "_")
        tardir = self.umlaut2plain(tardir)
        
        os.system("mkdir %s/%s" % (tempdir, tardir)) 
        out = u""
	firstPage = pages[0]
        for p in pages:
            text = WikiPage(self.env, p).text 
            temp = StringIO()
            
            TexFormatter(self.env, context, p, firstPage).format(text, temp, False)
            out += u"\n%%%%%%%%%%%%%%%%%%%%\n"
            out += u"%% %s\n" % p
            out += u"\label{%s}\n\n" % p.replace(" ", "-").replace("_", "-").replace("/","-")
            out += temp.getvalue().replace("#PAGE", p).replace("&lt;", "\\todo{").replace("&gt;", "}")
            plugindir = self.env.path

            # copy attachment images into tempdir 
            os.system("mkdir %s/%s/images" % (tempdir, tardir))
            p = self.umlaut2plain(p.replace(" ", "_"))
            os.system("cp %s/attachments/wiki/%s/* %s/%s/images" % (plugindir, p, tempdir, tardir))
 
        # Cut additional tabular cells
        out = out.replace('&  \\\\', '  \\\\')

        out = out.encode("utf-8")

        latexfilename = 'content.tex' 
        f = open("%s/%s/%s" % (tempdir, tardir, latexfilename), 'w')
        f.write(out)
        f.close()


        mainfilename = self.umlaut2plain(title.replace(' ', '-').replace('"', '').replace("'", ""))
        mainfilename = mainfilename + '.tex' 
        includetexfiles = [['template_url', mainfilename], ['macro_url', 'macros.tex']]
        utitle = self.umlaut2latex(title)
        usubject = self.umlaut2latex(subject)
        uversion = self.umlaut2latex(version)
        udate = self.umlaut2latex(date)
        for file in includetexfiles:
            path = self.env.config.get('wikiprintlatex', file[0])
            if file[1] == '':
                file[1] = path 
            try:
                f = open(path)
                text = f.read()
                f.close()
                text = text.replace('#TITLE', utitle.encode())
                text = text.replace('#SUBJECT', usubject.encode())
                text = text.replace('#VERSION', uversion.encode())
                text = text.replace('#DATE', udate.encode()) 
                r = open("%s/%s/%s" % (tempdir, tardir, file[1]), 'w')
                r.write(text)
                r.close()
            except IOError:
                raise TracError("Wasn't able to add primary file %s to tar archive" % path)

        includefiles = ['logo_url', 'additional_url']
        for file in includefiles:
            path = self.env.config.get('wikiprintlatex', file)
            try:
                f = open(path)
                content = f.read()
                f.close()
                if file == 'logo_url':
                    imagedir = "/images"
                else:
                    imagedir = ""
                r = open("%s/%s%s/%s" % (tempdir, tardir, imagedir, os.path.basename(path)), 'w') 
                r.write(content)
                r.close()
            except IOError:
                raise TracError("Wasn't able to add additional or logo file %s to tar archive" % path)
 
        filename = 'request.tar'
        os.system("cd %s && tar -cvf %s %s" % (tempdir, filename, tardir))

        req.send_header('Content-Disposition', 'attachment; filename=' + filename)

        f = open("%s/%s" % (tempdir, filename), 'r')
        out = f.read()  

        # send content of tar-file
        req.send_header('Content-Length', len(out))
        req.end_headers()
        req.write(out)
        
        # clean tempdir
        os.system("rm -r %s" % tempdir)

        raise RequestDone

class TexFormatter(Formatter):

    pictures = []

    def __init__(self, env, context, path, basepath, begindoc = False):
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

	self.path = path
	self.basepath = basepath

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

    def _lhref_formatter(self, match, fullmatch):
        rel = fullmatch.group('rel')
        ns = fullmatch.group('lns')
        target = self._unquote(fullmatch.group('ltgt'))
        label = fullmatch.group('label')
        if not label: # e.g. `[http://target]` or `[wiki:target]`
            if target:
                if target.startswith('//'): # for `[http://target]`
                    label = ns+':'+target   #  use `http://target`
                elif ns == 'ticket':
                    return r"\ticket{%s}" % target.split()[0]
                else:                       # for `wiki:target`
                    #return r"%s \ref{%s}" % (self.escape_verb(target), self.escape_verb(target).replace("#", ":").replace(" ", "").replace("_", ""))
                    return r"%s" % self.escape_verb(target)
        else:
            label = self._unquote(label)
        
        if not target:
            target = ""

        return self.wpl_make_link(ns, target, match, label)

    def wpl_make_link(self, ns, target, match, label):
        # first check for an alias defined in trac.ini
        ns = self.env.config.get('intertrac', ns) or ns

        if ns in self.wikiparser.link_resolvers:
            if target[0] != "#":
                #return r"%s \ref{%s}" % (self.escape_verb(label), self.escape_verb(target).replace("#", ":").replace(" ", "").replace("_", ""))
                return r"%s" % self.escape_verb(label)
            return r"\ticket{%s}" % target.split('#')[1]
        elif target.startswith('//') or ns == "mailto":
            return self.wpl_make_ext_link(ns+':'+target, label)
        elif label:
            return label
        else:
            return match

    def wpl_make_ext_link(self, url, text, title=''):
        text = self._latexescape_comments(text, None)
        url = self._latexescape_comments(url, None)
        if text == url:
            return r"\href{%s}{%s}" % (url, url)
        else:
            return r"\href{%s}{%s}" % (url, text)

    # Headings

    def _parse_heading(self, match, fullmatch, shorten):
        match = match.strip()

        depth = min(len(fullmatch.group('hdepth')), 5)
        anchor = fullmatch.group('hanchor') or ''
        heading_text = match[depth+1:-depth-1-len(anchor)]
        heading = wiki_to_oneliner(self.env, heading_text, self.path, self.basepath, self.db, False,
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
	anchor = anchor.replace(" ", "-").replace("_", "-").replace("/","-")
	depth = depth + self.path.count('/') - self.basepath.count('/')
        if depth > 1:
            self.out.write(os.linesep + ('\%ssection{%s}\n\label{#PAGE:%s}\n' % ("sub" * (depth - 2), heading, anchor)) + os.linesep)
        elif depth == 1:
            self.out.write(os.linesep + ('\chapter{%s}\n\label{#PAGE:%s}\n' % (heading, anchor)) + os.linesep)

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
            tmp = os.linesep + r'\begin{description}' + os.linesep

        definition = match[:match.find('::')]
        tmp += r'\item{%s}' % wiki_to_oneliner(self.env, definition, self.db)
        tmp += os.linesep
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
            self.out.write(os.linesep + os.linesep + r'\noindent' + os.linesep + r'\wikiprintlatextable{' + os.linesep)

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
            self.out.write(r' \\ ')

    def wpl_close_table(self):
        if self.in_table:
            self.wpl_close_table_row()
            self.out.write(r'\hline' + os.linesep)
            self.out.write(r'}{%s|}' % ("| l " * (self.max_cols - 1)) + os.linesep + os.linesep)
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
        self.wpl_set_list_depth(ldepth, type_, class_, start)
        return ''

    def wpl_get_list_depth(self):
        """Return the space offset associated to the deepest opened list."""
        try: 
            return self._list_stack and self._list_stack[-1][1] 
        except AttributeError:
            return 0 

    def wpl_set_list_depth(self, depth, new_type, list_class, start):
        def open_list():
            self.wpl_close_table()
            self.close_paragraph()
            self.close_indentation() # FIXME: why not lists in quotes?
            self._list_stack.append((new_type, depth))
            self._set_tab(depth)
            class_attr = list_class and ' class="%s"' % list_class or ''
            start_attr = start and ' start="%s"' % start or ''
            self.out.write (os.linesep + r'\begin{itemize}' + os.linesep)

            self.list_depth += 1
            self.out.write('\\item ')

        def close_list(tp):
            self._list_stack.pop()
            self.out.write (os.linesep + r'\end{itemize}' + os.linesep)

            self.list_depth -= 1

        # depending on the indent/dedent, open or close lists
        if depth > self.wpl_get_list_depth():
            open_list()
        else:
          try:  
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
                        self.out.write(os.linesep + '\\item ')
                else:
                    open_list()
          except AttributeError:
            ""

    def close_list(self):
        self.wpl_set_list_depth(0, None, None, None)

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
                            self.out.write(r'latex\begin{verbatim}' + os.linesep + self.code_text + os.linesep + r'\end{verbatim}')
                        else:
                            self.out.write(self.code_text)
                    else:
                        body = r'\begin{lstlisting}[language=%s]' %language + os.linesep + self.code_text + os.linesep + r'\end{lstlisting}'
                        self.out.write(os.linesep + body + os.linesep)
                else:
                    self.out.write(r'\begin{verbatim}' + os.linesep + self.code_text + os.linesep + r'\end{verbatim}')
            else:
                self.code_text += line + os.linesep
        elif not self.code_processor:
            match = WikiParser._processor_re.search(line)
            if match:
                self.code_processor = line[2:] # name
            else:
                self.code_text += line + os.linesep
                self.code_processor = None
        else:
            self.code_text += line + os.linesep

    def close_code_blocks(self):
        while self.in_code_block > 0:
            self.handle_code_block(WikiParser.ENDBLOCK)

    # WikiMacros

    def _macro_formatter(self, match, fullmatch):
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
            return None

    # -- Wiki engine

    def handle_match(self, fullmatch):
        for itype, match in fullmatch.groupdict().items():
            # handle ticket-links
            if match and match.startswith("#") and itype == "i3":
                if match[1:].isdigit():
                    return r"\ticket{%s}" % match[1:]
            if match and not itype in self.wikiparser.helper_patterns:
                # Check for preceding escape character '!'
                if match[0] == '!':
                    return self.escape_verb(escape(match[1:]))
                if itype in self.wikiparser.external_handlers:
                    if itype in ["i0", "i1", "i2"]:
                        return match

                    external_handler = self.wikiparser.external_handlers["i0"]

                    ret =  external_handler(self, match, fullmatch)
                    return ret
                else:
                    internal_handler = getattr(self, '_%s_formatter' % itype)
                    ret = internal_handler(match, fullmatch)
                    return ret

    # Pictures

    def _macrolink_formatter(self, match, fullmatch):
        if match[2:7].lower() == 'image':
            params = match[8:-3].split(',')
            width = ""
            caption = ""
            for param in params:
                param = param.strip()
                split = param.split('=')
                if split[0] == 'width':
                    width = '[' + param + ']' 
                elif split[0] == 'title':
                    caption = split[1]
                elif split[0] == 'height':
                    width = '[' + param + ']'  
            source = params[0]
            self.pictures.append(source)
            if source.endswith(".svg"):
                source = source[:-4]
            body = '\\begin{figure}[htbf]' + os.linesep
            body += '\\includegraphics[width=0.95\\textwidth]{images/%s}' % (source) + os.linesep
            if caption:
                body += '\\caption{%s}' %caption + os.linesep
            body += '\\end{figure}' + os.linesep
            return body 
        else:
            return "" # TODO handle TitleIndex etc here
        

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

            self.out.write(result)
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

    def __init__(self, env, context, path, basepath):
        TexFormatter.__init__(self, env, context, path, basepath)

    def _macro_formatter(self, match, fullmatch):
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

def wiki_to_oneliner(env, wikitext, path, basepath, db=None, shorten=False, absurls=False, req=None):
    if not wikitext:
        return Markup()
    out = StringIO()
    context = Context.from_request(req, absurls=False)
    OneLinerTexFormatter(env, context,path,basepath).format(wikitext, out, shorten)
    return Markup(out.getvalue())

def latex_default_header():
    return ""

def latex_default_end():
    return ""


