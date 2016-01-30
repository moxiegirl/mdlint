#!/usr/bin/env python3

import sys, os, subprocess, collections


####################################################
# Report Class
class Report():
    """
    Class that generates a dict at Report.report containing
    relevant information on the state and progress of the GitBook 
    build, as well as stylistic and syntactic issues with the
    markdown source.
    """

    # Initialize the Class
    def __init__(self, arguments):
        """
        Method to initialize the Report() class.  Takes two arguments:
        itself and the parsed arguments given from the command line,
        begins the source file parsing.
        """

        # Set Class Variables
        self.args = arguments
        self.report = {
            "build_status": False,
            "build_warnings": {},
            "summary_orphans": [],
            "summary_duplicates": []
        }

        self.line_length = 72

        # Update source path and navigate into it.
        self.args.source_name = self.args.source
        self.args.source = os.path.abspath(self.args.source)

        basedir = os.curdir
        os.chdir(self.args.source)

        # Run the build and record errors
        if not self.args.nobuild:
            self.run_build()

        # Run the syntax checks and record errors
        if not self.args.nosyntax:
            self.run_syntax()

        # Print Report
        self.print_report()

    def run_build(self):
        """
        run_build() method calls GitBook to build the HTML documentation
          from the source files found in args.source.  It records the 
          output from this command in a variable and then parses it for 
          warnings, recording them at self.report['build_warnings'] and 
          self.report['build_status'].
        """

        command = ['node', '--stack-size=3200']

        # Determine GitBook Executable
        if sys.platform.lower() == 'linux':
            command.append('/usr/bin/gitbook')
        elif sys.platform.lower() == 'darwin':
            command.append('/usr/local/bin/gitbook')
        else:
            command = ['gitbook']

        # Add the Build Command, and the source directory
        html_command = command + ['build', self.args.source]
        # add pdf_command

        output = subprocess.check_output(html_command).decode().split('\n')
        for line in output:
            if '\x1b[0;33mwarn:' in line:
                self.report['build_warnings'] = line
            elif 'Done, without error' in line:
                self.report['build_status'] = True




    # Check for syntactic and stylistic issues
    def run_syntax(self):
        """
        run_syntax() method runs syntactic and stylistic 
          checks on args.source.
        """

        # Generate a Manifest
        manifest = self.gen_manifest()
        if 'SUMMARY.md' in manifest:
            manifest.remove('SUMMARY.md')
            self.check_summary()



    # Generate a manifest of args.source
    def gen_manifest(self, ext = '.md', get_list = False):
        """
        gen_manifest() method reads the files found at args.source.
          It then parses this down to files with the given extension,
          returning a list of the available files.

          This is used mainly to sort out auto-save files from the source
          directory when building a files list to read.
        """

        manifest = []

        if self.args.buildall or get_list:

            baselist = os.listdir('.')
            ext_length = 0 - len(ext)
            for i in baselist:
                if i[ext_length:] == '.md':
                    manifest.append(i)

        return manifest
                

    # Check SUMMARY.md for Common Syntax and Style Issues
    def check_summary(self):
        """
        check_summary() method is triggered by a command-line option
          or due to mdlint registers a change to SUMMARY.md.  The method
          reads the SUMMARY.md file, examining the links to each entry
          to identify duplicates and orphans.
        """

        # Generate a Complete List of Source Files
        complete_list = self.gen_manifest('.md', True)
        complete_list.remove('SUMMARY.md')

        # Open SUMMARY.md
        f = open('SUMMARY.md', 'r')
        target_dir = {}
        target_dup = []
        count = 1

        # Parse SUMMARY.md for Links and Link Titles
        for line in f:
            linenum = str(count)
            link = self.parse_link(line)

            if link != None:
                target_dir[link[0]] = link[1]
                target_dup.append(link[0])

            # Increment Line
            count += 1

        f.close()

        # Check that source files and SUMMARY.md lists match
        for i in complete_list:
            try:
                check = target_dir[i]
            except:
                self.report['summary_orphans'].append(i)

        # Check for Duplication
        counter = collections.Counter(target_dup)
        for i in counter.items():
            if i[1] > 1:
                self.report['summary_duplicates'].append(i[0])


    # Parse Links
    def parse_link(self, raw_text):
        """
        parse_link() method receives link text written in markdown, it
          separates the link text from the href and returns a tuple 
          containing both.
        """
        text = raw_text.split('](')
        if len(text) > 1:
            title = text[0].split('[')[1]
            link = text[1].split(')')[0]
            return [link, title]

    #################################################
    # Format Output

    # Print Report to Stdout
    def print_report(self):
        """
        print_report() method is the final command run by this class.
          It formats the self.report object and prints its output in a
          clean, human readable style to stdout.
        """
        output = ''

        output += self.print_summary()

        output += '\n\n' + '=' * self.line_length + '\n'

        print(output)

    def print_summary(self):

        output = '\n\n' + '=' * self.line_length + '\n\n'
        output += 'Checks made SUMMARY.md\n'

        # Print Errors for Duplicate Files
        duplicates = self.report['summary_duplicates']
        dup_err_text = """
        While checking SUMMARY.md for errors, the following duplicate
        entires were found in the table of contents.  GitBook only writes
        the first instance of these files.  Since GitBook does not read
        duplicate entries, any files nested under the later occurring
        instance does not get written to the output.""" 

        dup_pass_text = """
        While checking SUMMARY.md for errors, no duplicate
        entries were found.  This means that GitBook writes all 
        files designated in the table of contents to the output."""
        
        if len(duplicates) > 0:
            output += self.format_heading(
                'Check for Duplicates............ [ERROR]', dup_err_text)
            output += self.print_list(duplicates)
        else:
            if self.args.verbose:
                output += self.format_heading(
                    'Check for Duplicates........ [PASSED]', dup_pass_text)


        # Print Errors for Orphaned Files
        orphans = self.report['summary_orphans']
        orphan_err_text = """
        While checking SUMMARY.md for errors, the following orphaned
        files were found in the %s source directory.  GitBook does 
        not write orphaned files to the output.""" % self.args.source_name

        orphan_pass_text = """
        While checking SUMMARY.md for errors, no orphaned files were
        found.  This means that GitBook writes all source files in
        %s to the output.""" % self.args.source_name

        if len(orphans) > 0:
            output += self.format_heading(
                'Check for Orphans............... [ERROR]', orphan_err_text)
            output += self.print_list(orphans)
        else:
            if self.args.verbose:
                output += self.format_heading(
                    'Check for Orphans........... [PASSED]', orphan_pass_text)

        if len(orphans) > 0 or len(duplicates) > 0 or self.args.verbose:
            return output
        else:
            return ''


    def print_list(self, manifest):
        output = ''
        for i in manifest:
            output += '\t   - ' + i + '\n'

        return output

    def format_heading(self, title, description):
        return '   ' + title + ": " + description + '\n'

