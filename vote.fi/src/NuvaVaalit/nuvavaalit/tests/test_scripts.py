# -*- coding: utf-8 -*-
from nuvavaalit.models import DBSession
from nuvavaalit.tests import init_testing_db
import random
import shutil
import tempfile
import transaction
import unittest
import os.path
import xlrd
import openpyxl


class TestCreateVoters(unittest.TestCase):
    """Tests for the voter creation script."""

    def setUp(self):
        self.basedir = tempfile.mkdtemp()
        init_testing_db()
        # Make "random" values consistent
        random.seed(1234567890)
        transaction.begin()

    def tearDown(self):
        shutil.rmtree(self.basedir)
        DBSession.remove()

    def filename(self, name):
        """Returns a filename within the test directory."""
        return os.path.join(self.basedir, name)

    def test_genpasswd(self):
        from nuvavaalit.scripts.populate import CreateVoters

        self.assertEquals(5, len(CreateVoters(None, None).genpasswd(5)))

    def test_run__no_existing_voters(self):
        """Tests a successful operation which creates the Voter instances and
        the associated filesystem artifacts. There are now existing Voters in
        the database.
        """
        from nuvavaalit.models import Voter
        from nuvavaalit.scripts.populate import CreateVoters
        session = DBSession()

        xlsx_file = self.filename('input.xlsx')
        output = self.filename('voters.xls')

        data = [
            ('Rögers', 'Bück Williäm', 'Sömewhere street', '04320', 'Helsinki'),
            ('Li', 'Jët Huan', 'Chinä road 23', '04300', 'Helsinki'),
            ('Cöllisiön', 'Näme Föö', 'Cöllider curve 4', '05400', 'Helsinki'),
            ('Cöllisiön', 'Näme Bär', 'Cöllider curve 7', '05400', 'Helsinki'),
            ]
        wb = openpyxl.Workbook()
        ws = wb.get_active_sheet()
        for row, values in enumerate(data, start=1):
            for col, value in enumerate(values, start=1):
                ws.cell(row=row, column=col).value = value
        wb.save(filename=xlsx_file)

        cs = CreateVoters(xlsx_file, output)

        # Make sure we don't have any existing voters.
        self.assertEquals(0, session.query(Voter).count())
        self.assertEquals(0, len(cs.usernames))

        cs.run()

        # Make sure the Excel sheet got created.
        self.assertTrue(os.path.exists(output))

        # Check the Itella list. All voters without a GSM or email must be present.
        wb = xlrd.open_workbook(filename=output)
        ws = wb.sheet_by_index(0)
        self.assertEquals(5, ws.nrows)
        self.assertEquals(6, ws.ncols)
        self.assertEquals(ws.cell_value(1, 0), u'buck.rogers')
        self.assertEquals(ws.cell_value(1, 1), u'7xs464kc')
        self.assertEquals(ws.cell_value(1, 2), u'Bück Williäm Rögers')
        self.assertEquals(ws.cell_value(1, 3), u'Sömewhere street')
        self.assertEquals(ws.cell_value(1, 4), u'04320')
        self.assertEquals(ws.cell_value(1, 5), u'Helsinki')

        # Check created Voter objects. All voters must be present.
        voters = session.query(Voter).order_by(Voter.username).all()
        self.assertEquals(4, len(voters))

        self.assertEquals(voters[0].username, u'buck.rogers')
        self.assertEquals(voters[0].firstname, u'Bück')
        self.assertEquals(voters[0].lastname, u'Rögers')

        self.assertEquals(voters[1].username, u'jet.li')
        self.assertEquals(voters[1].firstname, u'Jët')
        self.assertEquals(voters[1].lastname, u'Li')

        self.assertEquals(voters[2].username, u'name.b.collision')
        self.assertEquals(voters[2].firstname, u'Näme')
        self.assertEquals(voters[2].lastname, u'Cöllisiön')

        self.assertEquals(voters[3].username, u'name.collision')
        self.assertEquals(voters[3].firstname, u'Näme')
        self.assertEquals(voters[3].lastname, u'Cöllisiön')

    def test_genusername__no_duplicate(self):
        from nuvavaalit.models import Voter
        from nuvavaalit.scripts.populate import CreateVoters
        session = DBSession()

        cs = CreateVoters(None, None)

        # Make sure we don't have any existing voters.
        self.assertEquals(0, session.query(Voter).count())
        self.assertEquals(0, len(cs.usernames))

        self.assertEquals(u'kai.lautaportti', cs.genusername(u'Kai'.split(), u'Lautaportti'))
        self.assertEquals(u'pertti.pasanen', cs.genusername(u'Pertti Sakari'.split(), u'Pasanen'))
        self.assertEquals(u'fuu.bar.boo', cs.genusername(u'Füü'.split(), u'Bär bÖÖ'))

    def test_genusername__invalid_ascii_character(self):
        from nuvavaalit.models import Voter
        from nuvavaalit.scripts.populate import CreateVoters
        session = DBSession()

        cs = CreateVoters(None, None)

        # Make sure we don't have any existing voters.
        self.assertEquals(0, session.query(Voter).count())
        self.assertEquals(0, len(cs.usernames))

        self.assertEquals(u'kai.lauta-portti', cs.genusername(u'Käi'.split(), u"Läutä-pör'tti"))

    def test_genusername__duplicates(self):
        from nuvavaalit.models import Voter
        from nuvavaalit.scripts.populate import CreateVoters
        session = DBSession()

        cs = CreateVoters(None, None)

        # Make sure we don't have any existing voters.
        self.assertEquals(0, session.query(Voter).count())
        self.assertEquals(0, len(cs.usernames))

        # First username without duplicate.
        self.assertEquals(u'foo.boo', cs.genusername(u'Föö Büü'.split(), u'Böö'))
        # First duplicate uses the middle initial.
        self.assertEquals(u'foo.b.boo', cs.genusername(u'Föö Büü'.split(), u'Böö'))
        # Second duplicate uses the full middle name.
        self.assertEquals(u'foo.buu.boo', cs.genusername(u'Föö Büü'.split(), u'Böö'))
        # Subsequent duplicates use an increasing suffix without the middle name.
        self.assertEquals(u'foo.boo2', cs.genusername(u'Föö Büü'.split(), u'Böö'))
        self.assertEquals(u'foo.boo3', cs.genusername(u'Föö Büü'.split(), u'Böö'))

    def test_genusername__duplicates_wo_middlename_fallback(self):
        from nuvavaalit.models import Voter
        from nuvavaalit.scripts.populate import CreateVoters
        session = DBSession()

        cs = CreateVoters(None, None)

        # Make sure we don't have any existing voters.
        self.assertEquals(0, session.query(Voter).count())
        self.assertEquals(0, len(cs.usernames))

        # First username without duplicate.
        self.assertEquals(u'foo.boo', cs.genusername(u'Föö'.split(), u'Böö'))
        # Without middle name we start using suffixes right away.
        self.assertEquals(u'foo.boo2', cs.genusername(u'Föö'.split(), u'Böö'))
        self.assertEquals(u'foo.boo3', cs.genusername(u'Föö'.split(), u'Böö'))
