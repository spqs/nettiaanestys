# -*- coding: utf-8 -*-
from datetime import datetime
from nuvavaalit.models import DBSession
from nuvavaalit.tests import election_period
from nuvavaalit.tests import init_testing_db
from pyramid import testing
import unittest


class TestFormatPercentage(unittest.TestCase):
    """Tests for the percentage formatter."""

    def test_zero_divisor(self):
        from nuvavaalit.views.results import format_percentage

        self.assertEquals('0.0', format_percentage(100, 0))

    def test_single_digit(self):
        from nuvavaalit.views.results import format_percentage

        self.assertEquals('44.2', format_percentage(23, 52))


class TestSortHash(unittest.TestCase):
    """Tests for the sort_hash helper."""

    def test_unicode_support(self):
        """Assert that we support unicode values as parameters in addition
        to byte strings and primitives.
        """
        from nuvavaalit.views.results import sort_hash

        self.assertEquals(sort_hash(u'fööbär'), sort_hash('fööbär'))
        self.assertEquals(sort_hash(u'10'), sort_hash(10))

    def test_multiple_arguments(self):
        from nuvavaalit.views.results import sort_hash

        self.assertEquals(sort_hash('fööbär'), sort_hash('föö', u'bär'))


class TestResults(unittest.TestCase):
    """Tests for the results calculation logic."""

    maxDiff = None

    def setUp(self):
        from pyramid.session import UnencryptedCookieSessionFactoryConfig
        self.config = testing.setUp()
        self.config.add_route('vote', '/aanesta/{id}')
        self.config.add_route('thanks', '/kiitos')
        self.config.set_session_factory(UnencryptedCookieSessionFactoryConfig)
        self.config.add_static_view('static', 'nuvavaalit:views/templates/static')
        self.config.add_settings({
            'nuvavaalit.num_selected_candidates': '8',
            'nuvavaalit.election_period': election_period(
                datetime(2011, 2, 1), datetime(2011, 3, 1)),
        })
        init_testing_db()

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def test_no_votes(self):
        from nuvavaalit.models import Candidate
        from nuvavaalit.models import Voter
        from nuvavaalit.views.results import results

        session = DBSession()
        session.add(Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers'))
        session.add(Candidate(2, u'Steven', u'Seagal', u'No pain, no game', u''))
        session.add(Candidate(7, u'Jet', u'Li', u'Yin, yang', u''))
        session.add(Candidate(11, u'Jean-Claude', u'van Damme', u'No engrish', u''))
        session.flush()

        self.assertEquals(results(testing.DummyRequest(statsd=False)), {
            'others': [],
            'selected': [{'name': u'Li, Jet',
                          'number': 7,
                          'percentage': '0.0',
                          'votes': 0},
                         {'name': u'Seagal, Steven',
                          'number': 2,
                          'percentage': '0.0',
                          'votes': 0},
                         {'name': u'van Damme, Jean-Claude',
                          'number': 11,
                          'percentage': '0.0',
                          'votes': 0}],
            'threshold': 8,
            'total_votes': 0,
            'show_leftovers': False,
            'voting_percentage': '0.0'})

    def test_stable_sorting_of_equals(self):
        """Test that in case of a tie we get a stable but random sorting of candidates."""
        from nuvavaalit.models import Candidate
        from nuvavaalit.models import Vote
        from nuvavaalit.models import Voter
        from nuvavaalit.views.results import results

        session = DBSession()
        session.add(Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers'))
        session.add(Candidate(2, u'Steven', u'Seagal', u'No pain, no game', u''))
        session.add(Candidate(7, u'Jet', u'Li', u'Yin, yang', u''))
        session.add(Candidate(11, u'Jean-Claude', u'van Damme', u'No engrish', u''))
        session.flush()

        candidate_two = session.query(Candidate).filter_by(number=2).first()
        candidate_seven = session.query(Candidate).filter_by(number=7).first()

        session.add(Vote(candidate_two))
        session.add(Vote(candidate_seven))
        session.flush()

        self.assertEquals(results(testing.DummyRequest(statsd=False)), {
            'others': [],
            'selected': [{'name': u'Li, Jet',
                          'number': 7,
                          'percentage': '50.0',
                          'votes': 1},
                         {'name': u'Seagal, Steven',
                          'number': 2,
                          'percentage': '50.0',
                          'votes': 1},
                         {'name': u'van Damme, Jean-Claude',
                          'number': 11,
                          'percentage': '0.0',
                          'votes': 0}],
            'threshold': 8,
            'total_votes': 2,
            'show_leftovers': False,
            'voting_percentage': '200.0'})

        # Rendering the results again will result in the same relative ordering
        # of the equal votes.
        self.assertEquals(results(testing.DummyRequest(statsd=False)), {
            'others': [],
            'selected': [{'name': u'Li, Jet',
                          'number': 7,
                          'percentage': '50.0',
                          'votes': 1},
                         {'name': u'Seagal, Steven',
                          'number': 2,
                          'percentage': '50.0',
                          'votes': 1},
                         {'name': u'van Damme, Jean-Claude',
                          'number': 11,
                          'percentage': '0.0',
                          'votes': 0}],
            'threshold': 8,
            'total_votes': 2,
            'show_leftovers': False,
            'voting_percentage': '200.0'})

    def test_empty_votes_removed_from_results_listing(self):
        """Test that in case of a tie we get a stable but random sorting of candidates."""
        from nuvavaalit.models import Candidate
        from nuvavaalit.models import Vote
        from nuvavaalit.models import Voter
        from nuvavaalit.views.results import results

        session = DBSession()
        session.add(Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers'))
        session.add(Candidate(Candidate.EMPTY_CANDIDATE, u'empty', u'empty', u'empty', u'empty'))
        session.add(Candidate(2, u'Steven', u'Seagal', u'No pain, no game', u''))
        session.add(Candidate(7, u'Jet', u'Li', u'Yin, yang', u''))
        session.add(Candidate(11, u'Jean-Claude', u'van Damme', u'No engrish', u''))
        session.flush()

        candidate_two = session.query(Candidate).filter_by(number=2).first()
        candidate_seven = session.query(Candidate).filter_by(number=7).first()
        candidate_empty = session.query(Candidate).filter_by(number=Candidate.EMPTY_CANDIDATE).first()

        session.add(Vote(candidate_two))
        session.add(Vote(candidate_seven))
        session.add(Vote(candidate_empty))
        session.add(Vote(candidate_empty))
        session.flush()

        # The empty votes do not show up in the results listing but do
        # affect the number of votes, percentages, etc.
        self.assertEquals(results(testing.DummyRequest(statsd=False)), {
            'others': [],
            'selected': [
                {'name': u'Li, Jet',
                 'number': 7,
                 'percentage': '25.0',
                 'votes': 1},
                {'name': u'Seagal, Steven',
                 'number': 2,
                 'percentage': '25.0',
                 'votes': 1},
                {'name': u'van Damme, Jean-Claude',
                 'number': 11,
                 'percentage': '0.0',
                 'votes': 0}],
            'threshold': 8,
            'total_votes': 4,
            'show_leftovers': False,
            'voting_percentage': '400.0'})
