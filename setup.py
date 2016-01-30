#!/usr/bin/env python3

from distutils.core import setup
setup(name = 'mdlint',
      version = '0.1',
      description = 'Lint checker for Projects written in GitBook Markdown.',
      author = 'Kenneth P. J. Dyer',
      author_email = 'kenneth@avoceteditors.com',
      url='https://github.com/avoceteditors/mdlint',
      license = "BSD 3-clause",
      packages = ['mdlint'],
      scripts = ['mdlint/mdlint'],
      classifiers = [
          'Development Status :: 2 - Pre-Alpha',
          'Environment :: Console',
          'Programming Language :: Python :: 3 :: Only',
          'Topic :: Text Processing :: Markup'
      ]
)
