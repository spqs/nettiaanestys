# -*- coding: utf-8 -*-
from isounidecode import unidecode
from itertools import count
from nuvavaalit.models import Candidate
from nuvavaalit.models import DBSession
from nuvavaalit.models import Voter
from pyramid.paster import bootstrap
from repoze.filesafe import FileSafeDataManager
import argparse
import csv
import os.path
import progressbar
import random
import re
import sys
import transaction
import xlrd
import xlwt

# Regex to match the date of birth from client provided data.
RE_DOB = re.compile(r'^(?P<day>\d{2})(?P<month>\d{2})(?P<year>\d{2})xx$')
# Regex to remove invalid characters from usernames
RE_INVALID_CHARS = re.compile('[^a-z-]')

# Mapping of zipcodes to the appropriate postal areas.
CITIES = {
    '01450': u'Vantaa',
    '04260': u'Kerava',
    '04300': u'Tuusula',
    '04310': u'Tuusula',
    '04320': u'Tuusula',
    '04330': u'Lahela',
    '04340': u'Tuusula',
    '04350': u'Nahkela',
    '04360': u'Tuusula',
    '04370': u'Rusutjärvi',
    '04380': u'Tuusula',
    '04390': u'Jäniksenlinna',
    '04430': u'Järvenpää',
    '04440': u'Järvenpää',
    '04460': u'Nummenkylä',
    '04480': u'Haarajoki',
    '04500': u'Kellokoski',
    '05400': u'Jokela',
    '05430': u'Nuppulinna',
    '05450': u'Nukari',
}


def relpath(path):
    """Returns a (possibly) relative path."""
    return os.path.abspath(os.path.join(os.getcwd(), path))


def univalue(s):
    return s.strip().decode('utf-8')


def populate_candidates():
    """Populates the database with candidate information."""
    parser = argparse.ArgumentParser(description='Generates candidates in the database.')
    parser.add_argument('config', help='Path to a Paste configuration file, e.g. development.ini.')
    parser.add_argument('candidates', nargs='?', help='Path to a CSV file containing the candidate information.')
    args = parser.parse_args()

    env = bootstrap(relpath(args.config))

    session = DBSession()
    session.bind.echo = False
    # Create the candidate for empty votes.
    session.add(Candidate(Candidate.EMPTY_CANDIDATE, u'Tyhjä', u'', u'', u''))

    csv_file = relpath(args.candidates)
    reader = csv.reader(open(csv_file))

    print 'Reading candidates from', csv_file

    cnt = 0
    reader.next()

    for row in reader:
        number, firstname, lastname, slogan = row[:4]
        try:
            number = int(number.strip())
        except (TypeError, ValueError):
            print 'Invalid data: {}'.format(str(row))
            continue

        session.add(Candidate(number, univalue(firstname), univalue(lastname), univalue(slogan), u''))
        print 'Added {} {}, {}'.format(firstname, lastname, number)
        cnt += 1

    session.flush()
    transaction.commit()

    print "Created {} candidates.".format(cnt)
    env['closer']()


def populate_test_users():
    """Populates the database with test users."""
    parser = argparse.ArgumentParser(description='Generates test users in the database.')
    parser.add_argument('config', help='Path to a Paste configuration file, e.g. development.ini.')
    parser.add_argument('quantity', nargs='?', default=10, type=int, help='Number of test users to generate.')
    args = parser.parse_args()

    env = bootstrap(relpath(args.config))
    session = DBSession()
    session.bind.echo = False

    for i in xrange(1, args.quantity + 1):
        session.add(Voter(u'user{}'.format(i), u'testi', u'User #{}'.format(i), u'Fööbär'))

    session.flush()
    transaction.commit()

    print "Created {} test users".format(args.quantity)
    env['closer']()


class CreateVoters(object):
    """Creates the voter accounts based on CSV data.

    The steps taken are:

        1. Generate a unique username for all voters.

           The usernames are primarily generated as "firstname.lastname" and
           in the case of duplicates the middle name is used as the
           discriminator. Any collitions after using the middle name will be
           resolved with an monotonically increasing integer suffix starting
           from 2.

        2. Generate a password for all voters.

        3. Create the :py:class:`nuvavaalit.models.Voter` instances.

        4. Write an Excel spreadsheet of (username, password, name, address,
           zipcode, city) combinations to a file which will be
           sent to Itella.
    """

    def __init__(self, source_file, output):
        self.usernames = set()
        self.output = output
        self.source_file = source_file

    def run(self):
        session = DBSession()
        session.bind.echo = False

        # Join the repoze.filesafe manager in the transaction so that files will
        # be written only when a transaction commits successfully.
        filesafe = FileSafeDataManager()
        transaction.get().join(filesafe)

        # Query the currently existing usernames to avoid UNIQUE violations.
        self.usernames.update(username for cols in session.query(Voter.username).all() for username in cols)

        fh_itella = filesafe.createFile(self.output, 'w')

        # Excel worksheet for Itella
        wb_itella = xlwt.Workbook(encoding='utf-8')
        ws_itella = wb_itella.add_sheet('Hexagon IT')
        text_formatting = xlwt.easyxf(num_format_str='@')
        for col, header in enumerate([u'Tunnus', u'Salasana', u'Nimi', u'Osoite', u'Postinumero', u'Postitoimipaikka']):
            ws_itella.write(0, col, header, text_formatting)
        rows_itella = count(1)
        voter_count = 0

        self.header('Starting to process {}'.format(self.source_file))
        src_sheet = xlrd.open_workbook(self.source_file).sheet_by_index(0)
        pbar = progressbar.ProgressBar(widgets=[progressbar.Percentage(), progressbar.Bar()], maxval=src_sheet.nrows).start()

        for row in xrange(1, src_sheet.nrows):
            token, lastname, names, address, zipcode, city = [c.value for c in src_sheet.row_slice(row, 0, 6)]
            names = names.split()
            firstname = names[0]

            username = self.genusername(names, lastname)
            password = self.genpasswd()

            # Create the voter instance.
            session.add(Voter(username, password, firstname, lastname, token))

            # Write the Itella information
            row = rows_itella.next()

            for col, item in enumerate([username, password, u'{} {}'.format(u' '.join(names), lastname), address, zipcode, city]):
                ws_itella.write(row, col, item, text_formatting)

            voter_count += 1
            pbar.update(voter_count)

        wb_itella.save(fh_itella)
        fh_itella.close()

        session.flush()
        transaction.commit()
        pbar.finish()

        self.header('Finished processing')
        print 'Processed', voter_count, 'voters.'

    def header(self, message):
        print '-' * len(message)
        print message
        print '-' * len(message)

    def genpasswd(self, length=8, chars='abcdefhkmnprstuvwxyz23456789'):
        """Generate a random password of given length.

        :param length: The length of the password.
        :type length: int

        :param chars: Iterable of allowed characters in the password.
        :type chars: iter

        :rtype: unicode
        """
        return u''.join(random.choice(chars) for i in xrange(length))

    def genusername(self, firstnames, lastname):
        """Generates a username based on the given names.

        :param firstnames: A list of first names.
        :type firstnames: list

        :param lastname: Last name
        :type lastname: unicode

        :rtype: unicode
        """
        def normalize(value):
            """Normalizes a value by first changing all non-ascii characters to
            their 7-bit representative values and then removing any invalid
            characters.
            """
            return unicode(RE_INVALID_CHARS.sub('', unidecode(value).lower()))

        # Generate a list of normalized first names.
        names = [normalize(n) for n in firstnames]
        # In case the lastname consists of multiple parts we join them with
        # a period.
        lastname = u'.'.join(normalize(n) for n in lastname.strip().split())

        # Try the "firstname.lastname" option first.
        candidate = u'{}.{}'.format(names[0], lastname)
        if candidate not in self.usernames:
            self.usernames.add(candidate)
            return candidate

        # If a second name exists, try using the first letter.
        if len(names) > 1 and len(names[1]) > 0:
            candidate = u'{}.{}.{}'.format(names[0], names[1][0], lastname)
            if candidate not in self.usernames:
                self.usernames.add(candidate)
                #print >> sys.stderr, "-!- Using middle initial for {}.".format(candidate)
                return candidate
            else:
                # Try with the whole second name.
                candidate = u'{}.{}.{}'.format(names[0], names[1], lastname)
                if candidate not in self.usernames:
                    self.usernames.add(candidate)
                    #print >> sys.stderr, "-!- Using middle name for {}.".format(candidate)
                    return candidate

        # We've exhausted our options of readable usernames, start using a suffix.
        suffix = count(2)
        candidate = base = u'{}.{}'.format(names[0], lastname)
        while candidate in self.usernames:
            candidate = u'{}{}'.format(base, suffix.next())

        self.usernames.add(candidate)
        #print >> sys.stderr, "-!- Using suffix for {}.".format(candidate)
        return candidate


def populate_voters():
    """Populates the database with Voter instances and generates an Excel sheet to be
    submitted to Itella.
    """
    parser = argparse.ArgumentParser(description='Populates the database with Voter instances.')
    parser.add_argument('config', help='Path to a Paste configuration file, e.g. development.ini.')
    parser.add_argument('voters', help='Excel file containing the original voter information.', nargs='?')
    parser.add_argument('output', help='Name of the Excel file where the voter information will be generated.', nargs='?', default='voters.xls')
    args = parser.parse_args()

    env = bootstrap(relpath(args.config))
    CreateVoters(relpath(args.voters), relpath(args.output)).run()
    env['closer']()


def verify_voters():
    """Checks the username/password combinations in the generated Excel sheet
    against the values stored in the database to ensure their consistency.
    """
    parser = argparse.ArgumentParser(description='Verify voter passwords.')
    parser.add_argument('config', help='Path to a Paste configuration file, e.g. development.ini.')
    parser.add_argument('voters', help='Excel sheet containing the generated voter information.')
    args = parser.parse_args()

    env = bootstrap(relpath(args.config))
    session = DBSession()
    session.bind.echo = False
    voters = dict(session.query(Voter.username, Voter).all())

    print "Checking {} for username/password consistency with the database.".format(args.voters)
    failed = 0
    wb = xlrd.open_workbook(filename=relpath(args.voters))
    ws = wb.sheet_by_index(0)

    if len(voters) != ws.nrows - 1:
        print 'Mismatch in the number of voters in the database and Excel sheet'
        sys.exit(1)

    pbar = progressbar.ProgressBar(widgets=[progressbar.Percentage(), progressbar.Bar()], maxval=len(voters)).start()

    for row in xrange(1, ws.nrows):
        username = ws.cell_value(row, 0)
        password = ws.cell_value(row, 1)
        if username not in voters:
            print "Unknown username:", username
            failed += 1
        elif not voters[username].check_password(password):
            print "Password mismatch for username:", username
            failed += 1

        pbar.update(row)

    pbar.finish()

    print 'Checked {} users. Failures: {}'.format(len(voters), failed)

    env['closer']()
