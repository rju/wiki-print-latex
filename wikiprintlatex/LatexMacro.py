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
from trac.attachment import Attachment
from trac.mimeview.api import Context

import os, shutil, glob, time, re
from tempfile import *
from urllib import *

def my_lstrip(text, prefix):
    return text[len(prefix):]

def get_attachment_url(formatter, filename):
    module, id = 'wiki', 'WikiStart'
    path_info = formatter.req.path_info.split('/',2)
    if len(path_info) > 1:
        module = path_info[1]
    if len(path_info) > 2:
        id = path_info[2]
    prefix = 'raw-attachment'

    path = [unicode(p) for p in [prefix, module, id, filename, None] if p]
    return formatter.req.abs_href.base + '/' + '/'.join(path)

def get_attachment(env, filename, req, module=None, id=None):
    if not module or not id:
        module, id = 'wiki', 'WikiStart'
        path_info = req.path_info.split('/',2)
        if len(path_info) > 1:
            module = path_info[1]
        if len(path_info) > 2:
            id = path_info[2]

    basename = os.path.basename(filename)
    try:
        attachment = Attachment(env, module, id, basename)
        return attachment
    except Exception:
        return None #Attachment not found

def add_attachment(env, filename, time, req):
    module, id = 'wiki', 'WikiStart'
    path_info = req.path_info.split('/',2)

    if len(path_info) > 1:
        module = path_info[1]
    if len(path_info) > 2:
        id = path_info[2]

    fin = open(filename, "r")
    size = os.fstat(fin.fileno())[6]

    attachment = Attachment(env, module, id)
    old_attachment = get_attachment(env, filename, req, module, id)
    if old_attachment:
        old_attachment.delete()

    basename = os.path.basename(filename)
    attachment.insert(basename, fin, size, time)
    fin.close()

    return attachment

def clean_dir(tempdir):
    for f in glob.glob(os.path.join(tempdir ,"*")):
        os.unlink(f)
    os.rmdir(tempdir)

def run_command(tempdir, base, width, height, dpi):
    curdir = os.getcwd()
    os.chdir(tempdir)
    os.system("latex -interaction=nonstopmode %s.tex >> log" % base)
    os.system("dvips -E -o %s.eps %s.dvi >> log" % (base, base))
    os.system("epstopdf %s.eps >> log" % base)
    if width and height:
        os.system("convert -density %dx%d -resize %dx%d! %s.pdf %s.png >> log" % (dpi, dpi, width, height, base, base))
    elif width or height:
        if not width:
            width = -1
        else:
            height = -1
        os.system("convert -density %dx%d -resize %dx%d %s.pdf %s.png >> log" % (dpi, dpi, width, height, base, base))
    else:
        os.system("convert -density %dx%d %s.pdf %s.png >> log" % (dpi, dpi, base, base))
    os.chdir(curdir)

def find_file(env, filespec, req):
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
        else: # #ticket:attachment or WikiPage:attachment
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

##     if not url: # this is an attachment
##         from trac.attachment import Attachment
##         attachment = Attachment(env, module, id, file)
##         url = attachment.path
##         raw_url = attachment.path #(req, format='raw')

    return url

def save_file(dir_path, url, server):
    host, path = splithost(url)
    basename = os.path.basename(path)

    if not host:
        host = server

    name = os.path.join(dir_path, basename)
    urlretrieve(basejoin(host, url), name)

    return name

class LatexMacro(WikiMacroBase):
    r"""Latex WikiProcessor:
    Now you can specify small pieces of latex code into any wiki context, like WikiHtml.
    
    Ex.:
    {{{
       {{{
       #!Latex
       %label=fig_math
       %width=800
       %height=600
       %dpi=300
       %use=package[opts]:package_url
       $\frac{\alpha^{\beta^2}}{\delta + \alpha}$

       }}}
    }}}
    This code will produce a PNG file and a PDF file, both will be added to Attachments section.

    The parameters are specified as latex comments.

    %label  Picture label, default value is 'unnamed', if two differents blocks has the same label,
    just the last block will be rendered.

    %width  PNG and display width.

    %height PNG and display height.

    %dpi    Dots per Inch (resolution), default value is 300.

    """
    def expand_macro(self, formatter, name, content):
        tempdir = ""
        try:
            if not content:
                return ''

            name, width, height, dpi, use = self.parse_args(content)
            tempdir = self.setup_tmp_dir(content, name, use)

            run_command(tempdir, name, width, height, dpi)
            png = add_attachment(self.env, os.path.join(tempdir, name + ".png"), None, formatter.req)
            pdf = add_attachment(self.env, os.path.join(tempdir, name + ".pdf"), None, formatter.req)

            hr_png = get_attachment_url(formatter, name + ".png")
            hr_pdf = get_attachment_url(formatter, name + ".pdf")

            clean_dir(tempdir)
            return '<a href="%s?format=raw"><img src="%s"/></a>' % (hr_pdf, hr_png)

        except Exception, e:
            print "EXCEPTION: ", e

        return 'ERROR: Check log file: %s' % (tempdir + "/log")

    def setup_tmp_dir(self, content, name, use):
        tempdir = mkdtemp(prefix="wiki2latex")

        pkgs = []
        for f in use:
            pname = f.split("|")[0]
            if "|" in f:
                url = f.split("|")[1]
            else:
                url = None
            if "[" in pname:
                opts = pname.split("[")[1].split("]")[0]
            else:
                opts = None
                pname = pname.split("[")[0]

            pkgs.append((pname, opts, url))

        print pkgs

        f = open (os.path.join(tempdir, name + ".tex"), "w")
        f.write(r"\documentclass{article}")

        for p in pkgs:
            if p[2]:
                save_file(tempdir, p[2], None)
            if p[0]:
                if p[1]:
                    f.write("\usepackage[%s]{%s}" % (p[1],p[0]))
                else:
                    f.write("\usepackage{%s}" % p[0])

        f.write(r"\pagestyle{empty}\begin{document}")
        f.write(content)
        f.write(r"\end{document}")
        f.close()

        return tempdir

    def parse_args (self, content):
        expr = re.compile(r"^\s*[%]\s*label\s*=\s*(?P<value>[-_a-zA-Z0-9]+)\s*$")
        ew   = re.compile(r"^\s*[%]\s*width\s*=\s*(?P<value>[0-9]+)\s*$")
        eh   = re.compile(r"^\s*[%]\s*height\s*=\s*(?P<value>[0-9]+)\s*$")
        ed   = re.compile(r"^\s*[%]\s*dpi\s*=\s*(?P<value>[0-9]+)\s*$")
        eu   = re.compile(r"^\s*[%]\s*use\s*=\s*(?P<value>.*)\s*$")
        name = 'unnamed'
        width = "0"
        height = "0"
        dpi = "300"
        use = []
        for line in content.splitlines():
            result = expr.match(line)
            if result:
                name = result.groupdict()['value']

            result = ew.match(line)
            if result:
                width = result.groupdict()['value']

            result = eh.match(line)
            if result:
                height = result.groupdict()['value']

            result = ed.match(line)
            if result:
                dpi = result.groupdict()['value']

            result = eu.match(line)
            if result:
                use.append(result.groupdict()['value'])

        return (name, int(width), int(height), int(dpi), use)



class LatexRenderMacro(WikiMacroBase):
    r'''Like Latex WikiProcessor LatexRender macro is used to specify small pieces of latex code
    into any wiki context, but LatexRender support latex code specified in other files
    (svn, attachments) and support external dependecies.

    Ex.:
    {{{
    [[LatexRender(source:/docs/tex/math.tex,inc=mymacros.sty,inc=others.sty,width=800,height=600,dpi=300)]]
    }}}
    This example will produce the same two figures as LatexMacro using the tex file /docs/tex/math.tex in SVN
    with two external dependencies (\usepackage) in Attachments section.

    The first parameter must be a URL to source code. The parameter "inc" is used to specify the external
    dependency URL and the others parameters are the same as LatexMacro

    width
    height
    dpi

    You can use the parameter "code" to specify a latex source code.

    Ex.:
    {{{
    [[LatexRender(code="$\frac{\alpha}{\beta}$",inc=mymacros.sty,inc=others.sty,width=800,height=600,dpi=300)]]
    }}}
    '''
    def expand_macro(self, formatter, name, content):
        tempdir = ""
        try:
            if not content:
                return ''

            name, includes, width, height, dpi = self.parse_args(content)
            server = "http://" + formatter.req.server_name + ":" + str(formatter.req.server_port)

            tempdir = self.setup_tmp_dir(name, includes, server, formatter)
            basename = os.path.basename(name)
            base, ext = os.path.splitext(basename)
            filename = os.path.join(tempdir, basename)

            tex = get_attachment(self.env, filename, formatter.req)
            rm_tex = False
            if not tex:
                rm_tex = True
                tex = add_attachment(self.env, filename, time.time(), formatter.req)

            png = get_attachment(self.env, base + ".png", formatter.req)
            pdf = get_attachment(self.env, base + ".pdf", formatter.req)

            if not png or not pdf or tex.date != png.date or tex.date != pdf.date:
                run_command(tempdir, base, width, height, dpi)
                png = add_attachment(self.env, os.path.join(tempdir, base + ".png"), None, formatter.req)
                pdf = add_attachment(self.env, os.path.join(tempdir, base + ".pdf"), None, formatter.req)

            if rm_tex:
                tex.delete()

            hr_png = get_attachment_url(formatter, base + ".png")
            hr_pdf = get_attachment_url(formatter, base + ".pdf")

            clean_dir(tempdir)
            return '<a href="%s"><img src="%s"/></a>' % (hr_pdf, hr_png)

        except Exception, e:
            print "EXCEPTION: ", e

        return 'ERROR: Check log file: %s' % (tempdir + "/log")

    def setup_tmp_dir(self, name, includes, server, formatter):
        tempdir = mkdtemp(prefix="wiki2latex")
        tex = includes[0]
        tex = tex.strip(' ')
        if tex.startswith('code="'):
            f = open (os.path.join(tempdir, name), "w")
            f.write(r"\documentclass{article}\pagestyle{empty}\begin{document}")
            f.write(my_lstrip(tex, 'code="')[:-1])
            f.write(r"\end{document}")
            f.close()
        else:
            url = find_file (self.env, tex, formatter.req)
            if not url:
                url = get_attachment_url(formatter, tex)
            save_file(tempdir, url, server)

        for inc in includes[1:]:
            url = find_file (self.env, inc, req)
            if not url:
                url = get_attachment_url(formatter, inc)
            save_file(tempdir, url, server)

        return tempdir

    def parse_args(self, content):
        args = content.split(',')
        filename = args[0]
        label = "unnamed"
        if not filename.startswith('code="'):
            host, path = splithost(filename)
            basename = os.path.basename(path)
            label, ext = os.path.splitext(basename)

        includes = [args[0]]
        width = 0
        height = 0
        dpi = 300
        for arg in args[1:]:
            arg = arg.strip(' ')
            if arg.startswith("inc="):
                includes.append(my_lstrip(arg, "inc="))
            elif arg.startswith("width="):
                width = int(my_lstrip(arg, "width="))
            elif arg.startswith("height="):
                height = int(my_lstrip(arg, "height=")),
            elif arg.startswith("dpi="):
                dpi = int(my_lstrip(arg, "dpi="))
            elif arg.startswith("label=") and label == "unnamed":
                label = my_lstrip(arg, "label=")

        return (label + ".tex", includes, width, height, dpi)

