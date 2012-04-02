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

class TexLatexCmdMacro(WikiMacroBase):
    r'''This macro inform to Trac2Latex parser a latex command
    to be inserted.
    
    Ex.:
    {{{
    [[LatexCmd("\maketitle")]]
    }}}
    '''
    def expand_macro(self, formatter, name, content):
        return content.split('"')[1]

