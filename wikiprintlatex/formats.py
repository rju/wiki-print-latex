"""
Copyright (C) 2008 Prognus Software Livre - www.prognus.com.br
Author: Diorgenes Felipe Grzesiuk <diorgenes@prognus.com.br>
Modified by: Alvaro Iradier <alvaro.iradier@polartech.es>
"""

from trac.core import *
from trac.web.api import RequestDone
from trac.wiki.model import WikiPage
from api import IWikiPrintFormat
from wikiprintlatex import WikiPrint

class WikiPrintOutput(Component):
    """Add output formats TEX to the WikiPrintLatex plugin."""
    
    implements(IWikiPrintFormat)
        
    def wikiprintlatex_formats(self, req):
        yield 'pdfarticle', 'PDF Article'
        yield 'pdfbook', 'PDF Book'
        yield 'printhtml', 'HTML'
        
    def process_wikiprintlatex(self, req, format, title, subject, pages, version, date, pdfname):

        wikiprintlatex = WikiPrint(self.env)

        html_pages = [wikiprintlatex.wikipage_to_html(WikiPage(self.env, p).text, p, req) for p in pages]

        # Send the output
        req.send_response(200)
        req.send_header('Content-Type', {
            'pdfbook': 'application/pdf',
            'pdfarticle': 'application/pdf',
            'printhtml':'text/html'}[format])

        if format == 'pdfbook':
            out = wikiprintlatex.html_to_pdf(req, html_pages, book=True, title=title, subject=subject, version=version, date=date)
            req.send_header('Content-Disposition', 'attachment; filename=' + pdfname + '.pdf')
        elif format == 'pdfarticle':
            out = wikiprintlatex.html_to_pdf(req, html_pages, book=False, title=title, subject=subject, version=version, date=date)
            req.send_header('Content-Disposition', 'attachment; filename=' + pdfname + '.pdf')
        elif format == 'printhtml':
            out = wikiprintlatex.html_to_printhtml(req, html_pages, title=title, subject=subject, version=version, date=date)
        
        req.send_header('Content-Length', len(out))
        req.end_headers()
        req.write(out)
        raise RequestDone
    
    
