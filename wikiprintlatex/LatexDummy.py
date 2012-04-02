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

class LatexDummyMacro(WikiMacroBase):
    """Macro with no effect
    """
    def expand_macro(self, formatter, name, content):
        return ''

class LatexBeginDocMacro(WikiMacroBase):
    """HTML version for TexLatexBeginDocMacro
    """
    def expand_macro(self, formatter, name, content):
        return ''

class LatexEndDocMacro(WikiMacroBase):
    """HTML version for TexLatexEndDocMacro
    """
    def expand_macro(self, formatter, name, content):
        return ''

class LatexDocClsMacro(WikiMacroBase):
    """HTML version for TexLatexDocClsMacro
    """
    def expand_macro(self, formatter, name, content):
        return ''

class LatexGetResMacro(WikiMacroBase):
    """HTML version for TexLatexGetResMacro
    """
    def expand_macro(self, formatter, name, content):
        return ''

class LatexCmdMacro(WikiMacroBase):
    """HTML version for TexLatexCmdMacro
    """
    def expand_macro(self, formatter, name, content):
        ret = content.split('"')
        if len(ret) > 4 :
            return ret[3]
        else:
            return ''

class LatexUsePkgMacro(WikiMacroBase):
    """HTML version for TexLatexUsePkgMacro
    """
    def expand_macro(self, formatter, name, content):
        return ''

class LatexTableMacro(WikiMacroBase):
    """HTML version for TexLatexTableMacro
    """
    def expand_macro(self, formatter, name, content):
        return ''

class LatexLongTableMacro(WikiMacroBase):
    """HTML version for TexLatexLongTableMacro
    """
    def expand_macro(self, formatter, name, content):
        return ''

class LatexBasicHeadersMacro(WikiMacroBase):
    """HTML version for TexLatexBasicHeadersMacro
    """
    def expand_macro(self, formatter, name, content):
        return ''

class LatexSpecialCharMacro(WikiMacroBase):
    """HTML version for TexLatexSpecialCharMacro
    """
    def expand_macro(self, formatter, name, content):
        return content

class TexTracIniMacro(WikiMacroBase):
    """ Not supported yet or not useful in Latex enviroment.
    """
    def expand_macro(self, formatter, name, content):
        return ''

class TexTracAdminHelpMacro(WikiMacroBase):
    """ Not supported yet or not useful in Latex enviroment.
    """
    def expand_macro(self, formatter, name, content):
        return ''

class TexTitleIndexMacro(WikiMacroBase):
    """ Not supported yet or not useful in Latex enviroment.
    """
    def expand_macro(self, formatter, name, content):
        return ''

class TexTicketQueryMacro(WikiMacroBase):
    """ Not supported yet or not useful in Latex enviroment.
    """
    def expand_macro(self, formatter, name, content):
        return ''

class TexRecentChangesMacro(WikiMacroBase):
    """ Not supported yet or not useful in Latex enviroment.
    """
    def expand_macro(self, formatter, name, content):
        return ''

class TexPageOutlineMacro(WikiMacroBase):
    """ Not supported yet or not useful in Latex enviroment.
    """
    def expand_macro(self, formatter, name, content):
        return ''

class TexMacroListMacro(WikiMacroBase):
    """ Not supported yet or not useful in Latex enviroment.
    """
    def expand_macro(self, formatter, name, content):
        return ''

class TexInterTracMacro(WikiMacroBase):
    """ Not supported yet or not useful in Latex enviroment.
    """
    def expand_macro(self, formatter, name, content):
        return ''

class TexHelloWorldMacro(WikiMacroBase):
    """ Not supported yet or not useful in Latex enviroment.
    """
    def expand_macro(self, formatter, name, content):
        return ''

class TexTracGuideTocMacro(WikiMacroBase):
    """ Not supported yet or not useful in Latex enviroment.
    """
    def expand_macro(self, formatter, name, content):
        return ''

class TexLatexRenderMacro(WikiMacroBase):
    """ Not supported yet or not useful in Latex enviroment.
    """
    def expand_macro(self, formatter, name, content):
        return ''
