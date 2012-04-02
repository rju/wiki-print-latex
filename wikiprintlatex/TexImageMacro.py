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
from trac.util.html import Markup, html, escape
from trac.resource import get_resource_url, Resource

from tempfile import *
from urllib import *
import re, os

class TexImageMacro(WikiMacroBase):
    '''
    This is the Tex version of Image macro.
    '''
    def basename(self, url):
        host, path = splithost(url)
        name = os.path.basename(path)
        return name

    def find_file(self, env, formatter, filespec, req):
        # parse filespec argument to get module and id if contained.
        parts = filespec.split(':')
        raw_url = None
        url = None
        name = None
        if len(parts) == 3:                 # module:id:attachment
            if parts[0] in ['wiki', 'ticket']:
                module, id, file = parts
            else:
                return None
        elif len(parts) == 2:
            from trac.versioncontrol.web_ui import BrowserModule
            try:
                browser_links = [link for link,_ in
                                 BrowserModule(env).get_link_resolvers()]
            except Exception:
                browser_links = []
            if parts[0] in browser_links:   # source:path
                module, file = parts
                rev = None
                if '@' in file:
                    file, rev = file.split('@')
                url = req.href.browser(file, rev=rev)
                raw_url = req.href.browser(file, rev=rev, format='raw')
                name = self.basename(url)
            else: # #ticket:attachment or WikiPage:attachment
                # FIXME: do something generic about shorthand forms...
                id, file = parts
                if id and id[0] == '#':
                    module = 'ticket'
                    id = id[1:]
                elif id == 'htdocs':
                    raw_url = url = req.href.chrome('site', file)
                    name = self.basename(url)
                elif id in ('http', 'https', 'ftp'): # external URLs
                    raw_url = url = id+':'+file
                    name = self.basename(url)
                else:
                    module = 'wiki'

        elif len(parts) == 1:               # attachment
            # determine current object
            # FIXME: should be retrieved from the formatter...
            # ...and the formatter should be provided to the macro
            file = filespec
            module, id = 'wiki', 'WikiStart'
            path_info = req.path_info.split('/',2)
            if len(path_info) > 1:
                module = path_info[1]
            if len(path_info) > 2:
                id = path_info[2]
            if module not in ['wiki', 'ticket']:
                raise Exception('Cannot reference local attachment from here')
        else:
            raise Exception('No filespec given')

        if not url: # this is an attachment
            from trac.attachment import Attachment
            attachment = Resource(module, id).child('attachment', file)

            url = get_resource_url(env, attachment, formatter.href)
            raw_url = get_resource_url(env, attachment, formatter.href, format='raw')
            name = self.basename(url)

        return raw_url, name

    def parse_tex_args(self, url, args, style):
        keys = args.keys()
        if "border" in style.keys():
            border = style["border"]
        else:
            border = False

        if "title" in keys:
            caption = args["title"]
        else:
            caption = None

        if "texwidth" in keys:
            width = args["texwidth"]
        else:
            width = 0

        if "texheight" in keys:
            height = args["texheight"]
        else:
            height = 0

        if "id" in keys:
            label = args["id"]
        else:
            label = None

        if "align" in keys:
            align = args["align"]
        else:
            align = None

        base = ""
        if width and height:
            base = "\\includegraphics[width=%s,height=%s]{%s}" % (width, height, url)
        else:
            if width:
                base = "\\includegraphics[width=%s]{%s}" % (width, url)
            elif height:
                base = "\\includegraphics[height=%s]{%s}" % (height, url)
            else:
                base = "\\includegraphics{%s}" % url

        if border:
            base  = "\\setlength{\\fboxrule}{%s}\n\\fbox{%s}" % (border, base)

        if align:
            if align == "center":
                base = "\\begin{center}\n%s\n\\end{center}" % base
            elif align == "left":
                base = "\\begin{flushleft}\n%s\n\\end{flushleft}" % base
            elif align == "right":
                base = "\\begin{flushright}\n%s\n\\end{flushright}" % base

        if label or caption:
            if caption:
                base = "%s\n\\caption{%s}" % (base, caption)

            if label:
                base = "%s\n\\label{%s}" % (base, label)

            base = "\\begin{figure}[htbp]\n%s\n\\end{figure}" % base

        return base

    def save_file(self, dir_path, url, server):
        host, path = splithost(url)
        basename, ext = os.path.splitext(os.path.basename(path))
        dirname = os.path.dirname(path)

        if not host:
            host = server

        fd, name = mkstemp(dir = dir_path, suffix = basename)
        os.unlink(name)

        found = False
        if ext not in [".svg", ".pdf", ".epdf"]:
            for new_ext in [".svg", ".pdf", ".epdf"]:
                new_url = basejoin(host, dirname + "/" + basename + new_ext + "?format=raw")
                output, headers = urlretrieve(new_url, name + new_ext)
                if headers:
                    if "pdf" in str(headers.gettype()) or "svg" in str(headers.gettype()):
                        found = True
                        ext = new_ext
                        break
                    else:
                        continue
                else:
                    continue

        if not found:
            new_url = basejoin(host, dirname + "/" + basename + ext + "?format=raw")
            urlretrieve(new_url, name + ext)

        if ext == ".svg":
            os.system("svg2pdf %s.svg %s.pdf" % (name, name))
            ext = ".pdf"

        return name + ext

    def expand_macro(self, formatter, name, content):
        try:
            # args will be null if the macro is called without parenthesis.
            if not content:
                return ''
            # parse arguments
            # we expect the 1st argument to be a filename (filespec)
            req = formatter.req
            args = content.split(',')

            if len(args) == 0:
                raise Exception("No argument.")

            filespec = args[0]

            size_re = re.compile('[0-9]+%?$')
            attr_re = re.compile('(align|border|width|height|alt|texwidth|texheight'
                                 '|title|longdesc|class|id|usemap)=(.+)')
            quoted_re = re.compile("(?:[\"'])(.*)(?:[\"'])$")
            attr = {}
            style = {}
            nolink = False
            for arg in args[1:]:
                arg = arg.strip()
                if size_re.match(arg):
                    # 'width' keyword
                    attr['width'] = arg
                    continue
                if arg == 'nolink':
                    nolink = True
                    continue
                if arg in ('left', 'right', 'top', 'bottom'):
                    style['float'] = arg
                    continue
                match = attr_re.match(arg)
                if match:
                    key, val = match.groups()
                    m = quoted_re.search(val) # unquote "..." and '...'
                    if m:
                        val = m.group(1)
                    if key == 'align':
                        style['float'] = val
                        attr['align'] = val
                    elif key == 'border':
                        style['border'] = '%dpt' % int(val);
                    elif key == 'width' or key == 'height':
                        attr[str(key)] = '%dpt' % int(val);
                    else:
                        attr[str(key)] = val # will be used as a __call__ keyword
            if style:
                attr['style'] = '; '.join(['%s:%s' % (k, escape(v))
                                           for k, v in style.iteritems()])

            url, name = self.find_file (self.env, formatter, filespec, req)

            name = self.save_file(self.env.tempdir, url, "http://" + req.server_name + ":" + str(req.server_port))
            result = self.parse_tex_args(name, attr, style)
            return result

        except Exception, e:
            print "EXCEPTION", e, name, content
