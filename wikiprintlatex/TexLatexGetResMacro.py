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



class TexLatexGetResMacro(WikiMacroBase):
    r'''This macro inform to Trac2Latex parser a external dependency URL.
    This dependency (picture, package, document class, etc...) will
    be downloaded to a temporary directory.

    Ex.:
    {{{
    [[LatexGetRes(source:/docs/math.tex)]]
    }}}
    '''

    def basename(self, url):
        host, path = splithost(url)
        name = os.path.basename(path)
        return name

    def save_file(self, dir_path, name, url, server):
        host, path = splithost(url)

        if not host:
            host = server

        urlretrieve(basejoin(host, url), os.path.join(dir_path, name))
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

    def expand_macro(self, formatter, name, content):
        try:
            req = formatter.req
            url, name = self.find_file (self.env, formatter, content, req)
            package = self.save_file(self.env.tempdir, name, url, "http://" + req.server_name + ":" + str(req.server_port))
            return  ""

        except Exception, e:
            print "EXCEPTION:", e, name, content
        return content
