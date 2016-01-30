#!/usr/bin/env python3

from distutils.core import setup
setup(
    name = 'mdlint',
    version = '0.1',
    description = 'Lint checker for Projects written in GitBook Markdown.',
    author = 'Kenneth P. J. Dyer',
    author_email = 'kenneth@avoceteditors.com',
    url='https://github.com/avoceteditors/mdlint',
    packages = ['mdlint'],
    scripts = ['mdlint/mdlint']
)
