# -*- coding: utf-8 -*-
from datetime import datetime
from nuvavaalit.tests import election_period
from nuvavaalit.tests import init_testing_db
from nuvavaalit.tests import static_datetime
from pyramid import testing
import mock
import unittest


class TestRootFactory(unittest.TestCase):
    """Tests for the common root factory."""

    def setUp(self):
        self.config = testing.setUp()
        self.config.add_settings({
            'nuvavaalit.election_period': election_period(
                datetime(2011, 2, 1), datetime(2011, 3, 1)),
        })

    def tearDown(self):
        testing.tearDown()

    def test_no_matchdict(self):
        from nuvavaalit.models import RootFactory

        request = testing.DummyRequest(statsd=False)
        del request.matchdict

        self.assertFalse(hasattr(request, 'matchdict'))
        root = RootFactory(request)
        self.assertEquals(root.__dict__.keys(), ['__acl__'])

    def test_with_matchdict(self):
        from nuvavaalit.models import RootFactory

        request = testing.DummyRequest(statsd=False)
        request.matchdict.update({
            'foo': u'bär',
            'secret': 12345,
        })

        root = RootFactory(request)
        self.assertEquals(sorted(root.__dict__.keys()), ['__acl__', 'foo', 'secret'])
        self.assertEquals(getattr(root, 'foo'), u'bär')
        self.assertEquals(getattr(root, 'secret'), 12345)


class TestSchedule(unittest.TestCase):
    """Election scheduling tests."""

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def make_schedule(self):
        """Creates an election schedule."""
        from nuvavaalit.models import Schedule
        return Schedule(testing.DummyRequest(statsd=False))

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 1, 1)))
    def test_before_election_period(self):
        self.config.add_settings({
            'nuvavaalit.election_period': election_period(
                datetime(2011, 2, 1), datetime(2011, 3, 1)),
        })
        schedule = self.make_schedule()
        self.assertTrue(schedule.before_elections())
        self.assertFalse(schedule.during_elections())
        self.assertFalse(schedule.after_elections())

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 3, 24)))
    def test_during_election_period(self):
        self.config.add_settings({
            'nuvavaalit.election_period': election_period(
                datetime(2011, 3, 1), datetime(2011, 3, 30)),
        })
        schedule = self.make_schedule()
        self.assertFalse(schedule.before_elections())
        self.assertTrue(schedule.during_elections())
        self.assertFalse(schedule.after_elections())

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 4, 1)))
    def test_after_election_period(self):
        self.config.add_settings({
            'nuvavaalit.election_period': election_period(
                datetime(2011, 3, 1), datetime(2011, 3, 30)),
        })
        schedule = self.make_schedule()
        self.assertFalse(schedule.before_elections())
        self.assertFalse(schedule.during_elections())
        self.assertTrue(schedule.after_elections())

    def test_permissions__invalid_election_period(self):
        self.config.add_settings({
            'nuvavaalit.election_period': election_period(
                datetime(2011, 4, 1), datetime(2011, 3, 1)),
        })
        self.assertRaises(ValueError, lambda: self.make_schedule())

    def test_permissions__erronous_election_period(self):
        self.config.add_settings({
            'nuvavaalit.election_period': 'foo bar',
        })
        self.assertRaises(ValueError, lambda: self.make_schedule())

    def test_permissions__missing_election_period(self):
        self.assertRaises(ValueError, lambda: self.make_schedule())

    def test_permissions__partial_election_period(self):
        self.config.add_settings({
            'nuvavaalit.election_period': '2011-10-10 12:45',
        })
        self.assertRaises(ValueError, lambda: self.make_schedule())


class TestVoter(unittest.TestCase):
    """Voter tests."""

    def test_constructor(self):
        from nuvavaalit.models import Voter

        voter = Voter(u'buck_rogers', u'secret', u'Bück', u'Rögers')
        self.assertEquals(u'buck_rogers', voter.username)
        self.assertEquals(u'Bück', voter.firstname)
        self.assertEquals(u'Rögers', voter.lastname)

    def test_fullname(self):
        from nuvavaalit.models import Voter

        voter = Voter(u'buck_rogers', u'secret', u'Bück', u'Rögers')
        self.assertEquals(u'Bück Rögers', voter.fullname())


class TestCandidate(unittest.TestCase):
    """Docstring."""

    maxDiff = None

    def setUp(self):
        init_testing_db()

    def tearDown(self):
        from nuvavaalit.models import DBSession
        DBSession.remove()

    def test_is_empty(self):
        from nuvavaalit.models import Candidate

        empty = Candidate(Candidate.EMPTY_CANDIDATE, u'Empty', u'candidate', u'', u'')
        self.assertTrue(empty.is_empty())

        real = Candidate(69, u'Real', u'McCoy', u'', u'')
        self.assertNotEqual(69, Candidate.EMPTY_CANDIDATE)
        self.assertFalse(real.is_empty())

    def test_fullname__both_names(self):
        from nuvavaalit.models import Candidate

        candidate = Candidate(69, u'Reäl', u'McCöy', u'', u'')
        self.assertEquals(u'McCöy, Reäl', candidate.fullname())

    def test_fullname__firstname_only(self):
        from nuvavaalit.models import Candidate

        candidate = Candidate(69, u'', u'McCöy', u'', u'')
        self.assertEquals(u'McCöy', candidate.fullname())

    def test_fullname__lastname_only(self):
        from nuvavaalit.models import Candidate

        candidate = Candidate(69, u'Reäl', u'', u'', u'')
        self.assertEquals(u'Reäl', candidate.fullname())

    def test_repr(self):
        from nuvavaalit.models import Candidate

        candidate = Candidate(69, u'Reäl', u'McCöy', u'', u'')
        self.assertTrue(repr(candidate).startswith('<nuvavaalit.models.Candidate[name=McCöy, Reäl,number=69] at '), repr(candidate))
