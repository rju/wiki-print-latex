from trac.wiki.formatter import Formatter
from trac.wiki.macros import WikiMacroBase
from trac.mimeview.api import Context

from StringIO import StringIO

class IncludeMacro(WikiMacroBase):
    """
    Inserts the contents of another wiki page. It expands arguments in the page in the form {{N}}.

    Example:
    [[Include(wiki:WikiStart)]]


    WARNING: avoid recursive inclusion.

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
        codepage = self.env.config.get('trac', 'charset', 'ISO8859-15')

        Formatter(self.env, formatter.context).format(text, out, False)
        text = out.getvalue().encode(codepage)
        return text
