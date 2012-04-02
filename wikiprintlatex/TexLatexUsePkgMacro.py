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

from tempfile import *
from urllib import *
import re, os

class TexLatexUsePkgMacro(WikiMacroBase):
    r'''This macro inform to Trac2Latex parser a package to be used (\usepackage).

    Ex.:
    {{{
    [[LatexUsePkg(tabular)]]
    }}}
    '''
    def save_file(self, dir_path, url, server):
        host, path = splithost(url)
        basename = os.path.basename(path)
        dirname = os.path.dirname(path)

        if not host:
            host = server

        fd, name = mkstemp(dir = dir_path, suffix = basename)
        os.unlink(name)
        urlretrieve(basejoin(host, url + ".sty?format=raw"), name + ".sty")
        return name


    def get_file(self, filespec, req):
        # parse filespec argument to get module and id if contained.
        parts = filespec.split(':')
        url = None
        if len(parts) == 3:                 # module:id:attachment
            if parts[0] in ['wiki', 'ticket']:
                module, id, file = parts
            else:
                return None
        elif len(parts) == 2:
            from trac.versioncontrol.web_ui import BrowserModule
            try:
                browser_links = [link for link,_ in
                                 BrowserModule(self.env).get_link_resolvers()]
            except Exception:
                browser_links = []
            if parts[0] in browser_links:   # source:path
                module, file = parts
                rev = None
                if '@' in file:
                    file, rev = file.split('@')
                url = req.href.browser(file, rev=rev)
                raw_url = req.href.browser(file, rev=rev, format='raw')
            else: # #ticket:attachment or WikiPage:attachment
                # FIXME: do something generic about shorthand forms...
                id, file = parts
                if id and id[0] == '#':
                    module = 'ticket'
                    id = id[1:]
                elif id == 'htdocs':
                    raw_url = url = req.href.chrome('site', file)
                elif id in ('http', 'https', 'ftp'): # external URLs
                    raw_url = url = id+':'+file
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
            attachment = Attachment(self.env, module, id, file)
            url = attachment.href(req)
            raw_url = attachment.href(req, format='raw')

        return url

    def expand_macro(self, formatter, name, content):
        try:
            req = formatter.req
            args = content.split(",")
            package = args[0]
            args.remove(package)

            pkgargs  = None
            download = False
            arg = None
            for p in args:
                if "download" in p.lower():
                    arg = p
                    break

            if arg:
                if "true" in arg.lower():
                    download = True
                args.remove(arg)

            if len(args):
                pkgargs = ",".join(args)

            if download:
                url = self.get_file (package, req)
                package = self.save_file(self.env.tempdir, url, "http://" + req.server_name + ":" + str(req.server_port))

            if pkgargs:
                return  "\\usepackage[%s]{%s}" % (pkgargs, package)
            else:
                return  "\\usepackage{%s}" % package

        except Exception, e:
            print "EXCEPTION:", e
        return content
