# Module Imports
import os
import logging
import re
import sqlite3 as sqlite
import time
import prettytable
import subprocess

# Main Process
class Main():

    # Initialize Class
    def __init__(self, args):
        self.args = args
        self.report = {}

        # Configure Logging
        if self.args.verbose:
            loglevel = logging.DEBUG
        else:
            loglevel = logging.INFO
        logformat = '[%(levelname)s %(asctime)s]: %(msg)s'
        logging.basicConfig(filename = 'mdlint.log',
                            level = loglevel,
                            format = logformat)
        logging.info("Initializing MDLint.")

        # Define Directory/Source Paths
        self.cwd = os.getcwd()
        source = os.path.abspath(self.args.source)

        # Initialize Database
        self.database = LocalDatabase(self.args)
        
        # Generate File List
        self.source = self.generate_filelist(source)

        # Read Files
        if 'SUMMARY.md' in self.source or self.args.update:
            self.read_summary()

        # Update headings Table with correct links
        self.update_files(self.source)
        self.read_files(self.source)
        self.check_links()
        
        # Report Findings
        if self.args.verbose:
            self.print_report()

    ####################################################
    # Generate File List
    def generate_filelist(self, path):

        if 'SUMMARY.md' in self.args.source:
                path = os.path.abspath(path.split('SUMMARY.md')[0])
        
        if os.path.isfile(path):
            return [path]
        elif os.path.isdir(path):
                
            os.chdir(path)
            base = os.listdir('.')
            result = []
            cursor = self.database.get_cursor()
            
            for i in base:
                if i == None:
                    pass
                elif re.match('.*\.md$', i):
                    statement = 'SELECT * FROM repository WHERE filename = "%s"' % i
                    cursor.execute(statement)
                    fetch = cursor.fetchone()
                    modtime = os.path.getmtime(i)
                    if fetch == [] or fetch == None:
                        self.update_repository(cursor, i, modtime)
                        result.append(i)
                    else:
                        dbmtime = fetch['last_update']
                        if dbmtime < modtime:
                            self.update_repository(cursor, i, modtime)
                            result.append(i)
                            
                            
            cursor.close()
            self.database.commit()
            
            return result

        else:
            logging.critical("Unable to identify source files.")
            sys.exit(1)

    # Update Repository
    def update_repository(self, cursor, filename, modtime):
        statement = ("REPLACE INTO repository('filename', 'last_update')"
                     "VALUES('%s', %s)") % (filename, int(modtime))
        cursor.execute(statement)


    # Get Base File Data
    def get_filedata(self, filename):
        cursor = self.database.get_cursor()
        statement = 'SELECT * FROM repository WHERE filename = "%s"'
        cursor.execute(statement)
        data = cursor.fetchone()
        results = {
            'name': data['filename'],
            'id': data['id'],
        }
        cursor.close()
        return results

    # Link Parser
    def parse_link(self, text):
        work = text.strip()
        div = work.split('](')
        title = div[0].split('[')[1]
        base_link = div[1].split(')')[0]
        link = base_link


        return [title, link]

    # Update links
    def update_links(self, cursor, filename, lineno, link):
        # Get idref
        statement = 'SELECT * FROM repository WHERE filename = "%s"' % filename
        cursor.execute(statement)
        fetch = cursor.fetchone()
        if re.match('http://.*', link):
            self.log_exlink(cursor, fetch['id'], lineno, link)
        elif re.match('https://.*', link):
            self.log_exlink(cursor, fetch['id'], lineno, link)
        else:
            self.log_inlink(cursor, fetch['id'], lineno, link)

    # Log Internal Links
    def log_inlink(self, cursor, source_id, lineno, link):
        anchor = 'NULL'
        target_id = 'NULL'
        if link[0] == "#":
            anchor = '"%s"' % link.split('#')[1].lower()
            target_id = source_id
        elif "#" in link:
            base_link = link.split('#')
            anchor = '"%s"' % base_link[1].lower()
            target_file = base_link[0]
            target_id = self.get_idref(cursor, target_file)
        elif re.match('.*.md$', link):
            target_id = self.get_idref(cursor, link)

        base_statement = "INSERT INTO inlinks(source_file, target_file, valid, line, link_text, anchor) "
        validity = 1
        if target_id == None:
            target_id = "NULL"
            validity = 0

        # Manage Malformed Links
        if '"' in link:
            link = re.sub('\"', "", link)
            validity = 0
        elif '\\' in link:
            link = re.sub('\\', "", link)
            validity = 0

        predicate =  'VALUES(%s, %s, %s, "%s", %s, %s)' % (
            source_id, target_id, validity, link, lineno, anchor)
        statement = base_statement + predicate
        cursor.execute(statement)

    # Get File Idref
    def get_idref(self, cursor, filename):
        try:
            statement = 'SELECT * FROM repository WHERE filename = "%s"' % filename
            cursor.execute(statement)
            fetch = cursor.fetchone()
            if fetch != None:
                return fetch['id']
            else:
                return None
        except:
            return None
            
    # Log External Links
    def log_exlink(self, cursor, idref, lineno, link):

        statement = ("REPLACE INTO exlinks (href, file_id, valid, line)"
                     'VALUES ("%s", %s, %s, %s)') % (link, idref, 0, lineno)
    
    # Read SUMMARY.md
    def read_summary(self):
        # Init Cursor
        cursor = self.database.get_cursor()

        # Init Error Dict
        errors = {
            "duplicates": [],
            "orphans": []
        }
        
        # Reset Orphan and Duplicate Tags
        statement = ("UPDATE repository SET orphan = 1, duplicate = 0 "
                     'WHERE filename IS NOT "SUMMARY.md" '
                     'AND filename IS NOT "README.md"')
        cursor.execute(statement)
        
        # Init File Handler
        f = TextFileHandler('SUMMARY.md')
        contents = f.open()

        # Check Contents
        check = []
        lineno = 0
        for line in contents:
            # Increment Line Number
            lineno += 1

            # If Line Black or Heading, Skip
            if re.match('^[ \t\n]$', line) or line[0] == '#':
                pass
            else:
                # Break Line into Relevant units
                text = self.parse_link(line)
                title = text[0]
                link = text[1]
                # Register as Present
                statement = 'UPDATE repository SET orphan = 0 WHERE filename = "%s"' % link
                cursor.execute(statement)
                
                # Check for Duplication
                if link in check:
                    errors['duplicates'].append(link)
                    statement = 'UPDATE repository SET duplicate = 1 WHERE filename = "%s"' % link
                    cursor.execute(statement)
                check.append(link)


        # Commit Changes
        cursor.close()
        self.database.commit()

        # Report Orphans
        cursor = self.database.get_cursor()
        statement = 'SELECT * FROM repository WHERE orphan = 1'
        cursor.execute(statement)
        fetch = cursor.fetchall()
        for i in fetch:
            if i is not None:
                errors['orphans'].append(i['filename'])
        self.report["SUMMARY.md"] = errors
        cursor.close()
        f.close()


    ##############################
    # Print Report
    def print_report(self):
        output = ''
        for filename in self.report:
            if filename == 'SUMMARY.md':
                check = self.report['SUMMARY.md']
                output += self.format_summary(check)

        print(output)

    # Format Summary Errors
    def format_summary(self, report):
        output = ''

        # Log Duplicate Entries
        dup_report = []
        dup = False
        if report['duplicates'] == []:
            dup_report = ["\tNo duplicates found in SUMMARY.md.\n"]
        else:
            dup = True
            for entry in report["duplicates"]:
                line = ' - %s\n' % entry
                dup_report.append(line)

        # Log Orphans
        orph_report = []
        orph = False
        if report['orphans'] == []:
            orph_report = ["\tNo orphan files found in repository.\n"]
        else:
            orph = True
            for entry in report["orphans"]:
                if entry not in ["SUMMARY.md", "README.md"]:
                    line = ' - %s\n' % entry
                    orph_report.append(line)

        summary_short = """
Report on errors found in SUMMARY.md.  Currently, MDLint is able to identify 
two categories of errors in the GitBook toctree: duplicates and orphans.\n"""
       
        summary_long = """
Entries that it identifies as DUPLICATION indicates that there are two or more 
instances of this file in the table of contents.  This is a problem because GitBook 
only parses the first instance of a file in the toctree and ignores both all other 
instances and any files nested under all other instances, which can indicate that a 
significant body of the project is not rendering to output.

Meanwhile, files identified as ORPHANS are files present in the source repository, 
but absent in the table of contents.  These files do not appear in the output at all.\n"""
        
        if not dup and not orph:
            summary_text = summary_short
        else:
            summary_text = summary_short + summary_long

        header = self.heading_format("SUMMARY.md", summary_text)
        body = ''
        indent = [2, 3]
        duplicates = self.filelist_format(dup, indent, "DUPLICATES:", dup_report,
                                         "No duplicate files found.")
        orphans = self.filelist_format(orph, indent, "ORPHANS:", orph_report,
                                       "No orphan files found.")
        body = duplicates + '\n' + orphans
        return header + body
                                    

        

    def filelist_format(self, run, indent, title, filelist, fallback):
        headline = ' ' * indent[0] + title + '\n'
        body = ''
        if run:
            for i in filelist:
                body += ' ' * indent[1] + i
        else:
            body = ' ' * indent[1] + fallback + '\n'

        return headline + body

        
    def heading_format(self, title, text):
        header = body = ''
        dim = subprocess.check_output(['stty', 'size']).decode().split()
        width = 75
        clearance = len(title) + 10

        # Create the Header Line
        if width < clearance:
            header = clearance
        else:
            header = '%s  %s\n' % (title,'-' * (width - clearance))

        # Format Body
        indent = ' ' * 2
        length = 0
        for line in text.split('\n'):
            body += '%s%s\n' % (indent, line)
        body += '\n'
        return header + body

    ###############################
    # Parse Headings into Database
    def read_files(self, source):
        cursor = self.database.get_cursor()
        
        for i in source:

            # Open File
            f = TextFileHandler(i)
            contents = f.open()

            # Read Line by Line
            lineno = 0
            for line in contents:
                lineno += 1
                raw_links = re.findall("\[.*\]\(.*\)", line)
                for link in raw_links:
                    if link is not [] or not re.match('.'):
                        base_link = self.parse_link(link)
                        self.update_links(cursor, i, lineno, base_link[1])


            
            f.close()
        cursor.close()
        self.database.commit()

    # Update Database
    def update_files(self, source):
        cursor = self.database.get_cursor()
        for i in source:

            # Open File
            f = TextFileHandler(i)
            contents = f.open()

            # Find file_id for Current File
            statement = 'SELECT * FROM repository WHERE filename = "%s"' % i
            cursor.execute(statement)
            file_data = cursor.fetchone()

            idref = file_data["id"]

            
            # Read Line by Line
            lineno = 0
            for line in contents:
                if line[0] == '#':
                    anchor = self.parse_heading(line)
                    if anchor is not None:

                        # Insert New Anchor
                        statement = ("REPLACE INTO headings (anchor, file_id, line) "
                                     'VALUES ("%s", %s, %s)') % (anchor, idref, lineno)

                        cursor.execute(statement)
        cursor.close()
        self.database.commit()
                    
    def parse_heading(self, text):
        match = re.split("^#* ", text)
        if len(match) > 1:

            # Reduce Markdown Heading to Base Text
            base = match[1].strip()

            # Format
            subs = [
                ('`', ''),
                (' - ', '--'),
                ('"', ''),
                ("'",''),
                (' ','-')
            ]
            for sub in subs:
                base = re.subn(sub[0], sub[1], base)[0]
            
            return base.lower()


    # Check Links
    def check_links(self):
        cursor = self.database.get_cursor()
        for i in self.source:
            if i is not "SUMMARY.md":
                # Get Idref
                statement = 'SELECT * FROM repository WHERE filename = "%s"' % i
                cursor.execute(statement)
                fetch = cursor.fetchone()
                idref = fetch['id']

                # Get Links on Page
                statement = 'SELECT * FROM inlinks WHERE source_file = "%s"' % idref
                cursor.execute(statement)
                fetch = cursor.fetchall()
                for link in fetch:
                    link_id = link['id']
                    target = link["target_file"]
                    anchor = link["anchor"]
                    line = link["line"]
                    check_file = self.check_file_exists(cursor, target)
                    if check_file:
                        if anchor!= None:
                            check_anchor = self.check_anchor_exists(cursor, target, anchor)
                            if not check_anchor:
                                self.invalidate_link(cursor, link_id, "inlinks")

        
                    else:
                        self.invalidate_link(cursor,  link_id, 'inlinks')

    def invalidate_link(self, cursor, idref, table):
        statement = "UPDATE %s SET valid = 0 WHERE id = %s" % (table, idref)
        cursor.execute(statement)
        
    def check_file_exists (self, cursor, idref):
        statement = "SELECT * FROM repository WHERE id = %s" % idref
        try:
            cursor.execute(statement)
            return True
        except:
            return False

    def check_anchor_exists(self, cursor, idref, anchor):
        statement = "SELECT * FROM headings WHERE file_id = %s" % idref
        try:
            cursor.execute(statement)
            head = cursor.fetchall()
            check = False
            for i in head:
                check_anchor = i['anchor']
                if anchor == check_anchor:
                    check = True
            return check
        except:
            return False
            
    
#################################
# Local Database
class LocalDatabase():

    def __init__(self, args):
        self.args = args
        self.report = []

        # Initialize Database
        self.conn = sqlite.connect('mdlint.db')
        self.conn.row_factory = sqlite.Row
        
        # Check If New
        clock = time.strftime("%c")
        try:
            c = self.conn.cursor()
            c.execute("UPDATE information SET value = '%s' WHERE id = 1)" % clock)
            c.close()
            if self.args.update:
                self.init_db(clock)
        except:
            self.init_db(clock)


    # Initialize Database
    def init_db(self, clock):
        cursor = self.conn.cursor()
        schema = {
            "information": [
                "id INTEGER PRIMARY KEY AUTOINCREMENT",
                "field TEXT",
                "value TEXT"
            ],
            
            "repository": [
                "id INTEGER PRIMARY KEY AUTOINCREMENT",
                "filename TEXT UNIQUE",
                "last_update INTEGER",
                "orphan INTEGER",
                "duplicate INTEGER"
            ],
            
            "headings": [
                "id INTEGER PRIMARY KEY AUTOINCREMENT",
                "anchor TEXT",
                "file_id INTEGER",
                "line INTEGER"
            ],

            "inlinks": [
                "id INTEGER PRIMARY KEY AUTOINCREMENT",
                "source_file TEXT",
                "target_file TEXT",
                "valid INTEGER",
                "link_text TEXT",
                "anchor TEXT",
                "line INTEGER"
            ],
            "exlinks": [
                "id INTEGER PRIMARY KEY AUTOINCREMENT",
                "href TEXT",
                "file_id INTEGER",
                "valid INTEGER",
                "last_check TEXT"
            ]
        }
        
        for i in schema:
            statement = "CREATE TABLE IF NOT EXISTS %s (%s)" % (i, ', '.join(schema[i]))
            cursor.execute(statement)

        # Update Information
        try:
            query = "SELECT id FROM information WHERE field = 'db_created'"
            cursor.execute(query)
            statement = "UPDATE information SET value = '%s' WHERE id = 1)" % clock
            cursor.execute(statement)
        except:
            statement = ("INSERT INTO information ('field', 'value') "
                         "VALUES('db_created', '%s')") % clock
            cursor.execute(statement)
            statement = ("INSERT INTO information ('field', 'value') "
                         "VALUES('db_last_update', '%s')") % clock
            cursor.execute(statement)
        cursor.close()
        self.conn.commit()

    # Get Cursor
    def get_cursor(self):
        return self.conn.cursor()

    # Commit
    def commit(self):
        self.conn.commit()
    
    # Designate Orphans
    def set_orphan(self, filename):
        cursor = self.conn.cursor()
        statement = "UPDATE repository SET orphan = 1 WHERE filename = '%s'" % filename
        cursor.execute(statement)
        cursor.close()


##################################
# File Handler
class TextFileHandler():

    def __init__(self, filename):
        self.filename = filename

    def open(self):
        self.readfile = open(self.filename, 'r')
        return self.readfile
    
    def close(self):
        self.readfile.close()
        
