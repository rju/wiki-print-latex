from setuptools import setup

PACKAGE = 'WikiPrintLatex'
VERSION = '0.1'

setup(name = 'TracWikiPrintLatex',
    version = '0.1',
    packages = ['wikiprintlatex'],
    package_data = { 'wikiprintlatex' : [ 'templates/*', 'htdocs/js/*' ] },
    author = 'Gregor Hoops',
    author_email = 'grh@informatik.uni-kiel.de',
    description = 'A plugin for exporting Trac wiki pages as Latex files, based on Trac2Latex and Wikiprint plugin.',
    url = '',
    entry_points = {
        'trac.plugins': [
#            'wikiprintlatex.web_ui = wikiprintlatex.web_ui',
#            'wikiprintlatex.formats = wikiprintlatex.formats',
            'wikiprintlatex.wikiprintlatex = wikiprintlatex.wikiprintlatex',
        ],
    },
)

