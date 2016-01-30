=======
mdlint
=======

MDLint is a basic lint utility for documentation projects written using GitBook Markdown.  When run, it scans the source directory and performs basic syntax and style checks on the Markdown.  It then formats its founding, printing them to stdout.

Currently, it works on Linux.  It should also work on Mac OS X and Windows, but has not yet been tested on either.


-------------
Installation
-------------

MDLint is available in two versions: a stable release through the Python Package Index or a development release through GitHub.  

.. note:: During this early 0.x release cycle, PyPI and GitHub are kept more or less in alignment with each other.  This changes starting with 1.x releases, where only major versions are pushed to PyPI.

- To install MDLint through PyPI, run the following command:

  .. code-block:: console

     $ pip install mdlint --user

- To install MDLint through GitHub, complete the following steps:

  #. Clone the Git repository to your local machine:

     .. code-block:: console

	$ git clone https://github.com/avoceteditors/mdlint

  #. Enter the ``mdlint/`` and run the installation:

     .. code-block:: console

	$ cd mdlint/
	$ python3 setup.py install --user

MDLint is now installed on your system.


---------------
Usage
---------------

*TBD*




---------------
Contribution
---------------

This application is currently under develop, so expect things to change at random from until the 1.0 release.  If you find a particularly glaring error, create an issue or submit a pull request.



---------------
History
---------------

- **Version 0.1 [2016-01-30]** Initial development release.  Initial upload to PyPI.  MDLint finds and parses SUMMARY.md and the source directory, reporting duplicate entries and orphaned files.



