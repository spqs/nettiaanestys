from datetime import datetime
from nuvavaalit.models import DBSession
from nuvavaalit.tests import election_period
from nuvavaalit.tests import init_testing_db
from nuvavaalit.tests import static_datetime
from pyramid import testing
import mock
import unittest


class TestBrowseCandidates(unittest.TestCase):
    """Tests for the candidate browsing page."""

    maxDiff = None

    def setUp(self):
        self.config = testing.setUp()
        self.config.add_route('browse_candidates', '/ehdokkaat')
        self.config.add_route('login', '/tunnistaudu')
        self.config.add_route('results', '/tulokset')
        self.config.add_static_view('static', 'nuvavaalit:views/templates/static')
        self.config.add_settings({
            'nuvavaalit.election_period': election_period(
                datetime(2011, 2, 1), datetime(2011, 3, 1)),
        })
        init_testing_db()

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def test_candidates(self):
        from nuvavaalit.models import Candidate
        from nuvavaalit.views.public import browse_candidates

        session = DBSession()
        session.add(Candidate(2, u'Steven', u'Seagal', u'No pain, no game', u''))
        session.add(Candidate(7, u'Jet', u'Li', u'Yin, yang', u''))
        session.add(Candidate(11, u'Jean-Claude', u'van Damme', u'No engrish', u''))
        session.flush()

        options = browse_candidates(testing.DummyRequest(statsd=False))
        positions = options.pop('positions')
        self.assertEquals('0 1:3 2:3 0 1:3 2:3'.split(), [positions.next() for i in xrange(6)])
        self.assertEquals(list(options.pop('candidates')), [
            [{'image_url': 'http://example.com/static/images/candidates/2.jpg',
              'name': u'Seagal, Steven',
              'number': 2,
              'slogan': u'No pain, no game'},
             {'image_url': 'http://example.com/static/images/candidates/7.jpg',
              'name': u'Li, Jet',
              'number': 7,
              'slogan': u'Yin, yang'},
             {'image_url': 'http://example.com/static/images/candidates/11.jpg',
              'name': u'van Damme, Jean-Claude',
              'number': 11,
              'slogan': u'No engrish'}]])
        self.assertEquals(options, {
            'columns': 3,
            'page_name': 'browse'})


class TestHomePage(unittest.TestCase):
    """Tests for the home page view."""

    maxDiff = None

    def setUp(self):
        self.config = testing.setUp()
        self.config.add_route('browse_candidates', '/ehdokkaat')
        self.config.add_route('login', '/tunnistaudu')
        self.config.add_route('results', '/tulokset')
        self.config.add_settings({
            'nuvavaalit.election_period': election_period(
                datetime(2011, 2, 1), datetime(2011, 3, 1)),
        })
        init_testing_db()

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 1, 15)))
    def test_before_elections(self):
        """Assert that before elections the front page renders itself."""
        from nuvavaalit.models import Schedule
        from nuvavaalit.views.public import home

        request = testing.DummyRequest(statsd=False)
        self.assertTrue(Schedule(request).before_elections())
        self.assertEquals(home(request), {
            'browse_url': 'http://example.com/ehdokkaat'})

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 2, 15)))
    def test_during_elections(self):
        """Assert that during elections the front page redirects to the login page."""
        from nuvavaalit.models import Schedule
        from nuvavaalit.views.public import home

        request = testing.DummyRequest(statsd=False)
        self.assertTrue(Schedule(request).during_elections())
        response = home(request)
        self.assertEquals(response.status, '302 Found')
        self.assertEquals(response.location, 'http://example.com/tunnistaudu')

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 3, 15)))
    def test_after_elections(self):
        """Assert that after elections the front page redirects to the results page."""
        from nuvavaalit.models import Schedule
        from nuvavaalit.views.public import home

        request = testing.DummyRequest(statsd=False)
        self.assertTrue(Schedule(request).after_elections())
        response = home(request)
        self.assertEquals(response.status, '302 Found')
        self.assertEquals(response.location, 'http://example.com/tulokset')


class TestUtils(unittest.TestCase):
    """Test the utility functions."""

    maxDiff = None

    def test_split_candidates__boundary_cases(self):
        from nuvavaalit.views.public import split_candidates

        candidates = range(1)
        columns = list(split_candidates(candidates, 3))
        self.assertEquals(1, len(columns))
        self.assertEquals(columns, [[0]])

        candidates = range(2)
        columns = list(split_candidates(candidates, 3))
        self.assertEquals(1, len(columns))
        self.assertEquals(columns, [[0, 1]])

        candidates = range(3)
        columns = list(split_candidates(candidates, 3))
        self.assertEquals(1, len(columns))
        self.assertEquals(columns, [[0, 1, 2]])

        candidates = range(4)
        columns = list(split_candidates(candidates, 3))
        self.assertEquals(2, len(columns))
        self.assertEquals(columns, [[0, 1, 2], [3]])

    def test_split_candidates__divisible_by_columns(self):
        from nuvavaalit.views.public import split_candidates

        candidates = range(12)
        columns = list(split_candidates(candidates, 3))

        self.assertEquals(4, len(columns))
        self.assertEquals(columns, [
            [0, 1, 2],
            [3, 4, 5],
            [6, 7, 8],
            [9, 10, 11]])

    def test_split_candidate__odd_sized_columns(self):
        from nuvavaalit.views.public import split_candidates

        candidates = range(13)
        columns = list(split_candidates(candidates, 3))

        self.assertEquals(5, len(columns))
        self.assertEquals(columns, [
            [0, 1, 2],
            [3, 4, 5],
            [6, 7, 8],
            [9, 10, 11],
            [12]])
