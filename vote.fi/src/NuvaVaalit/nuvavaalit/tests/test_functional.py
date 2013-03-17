# -*- coding: utf-8 -*-
from Cookie import SimpleCookie
from datetime import datetime
from nuvavaalit.models import DBSession
from nuvavaalit.tests import election_period
from nuvavaalit.tests import static_datetime
from pyramid import testing
from pyramid.interfaces import IAuthenticationPolicy
import mock
import re
import shutil
import tempfile
import unittest
import webtest

TEST_CONFIG = {
    'sqlalchemy.url': 'sqlite://',
    'session.key': 'nuvavaalit',
    'session.cookie_expires': 'true',
    'session.type': 'ext:memcached',
    'session.url': '127.0.0.1:11211',
    'session.auto': 'true',
    'session.validate_key': 'somesecretkeytoperformaesoperations',
    'session.timeout': '3600',
    'nuvavaalit.num_selected_candidates': '8',
    'nuvavaalit.election_period': election_period(
        datetime(2011, 2, 1), datetime(2011, 3, 1)),
}


class FunctionalTestCase(unittest.TestCase):
    """Functional test base class."""

    maxDiff = None

    def setUp(self):
        self.lock_dir = tempfile.mkdtemp()
        self.testapp = self.make_app(self.lock_dir)

    def tearDown(self):
        DBSession.remove()
        shutil.rmtree(self.lock_dir)

    def make_app(self, lock_dir):
        """Creates the test application."""
        from nuvavaalit import main

        config = TEST_CONFIG.copy()
        config['session.lock_dir'] = lock_dir

        app = main({}, **config)
        return webtest.TestApp(app, extra_environ=dict(REMOTE_ADDR='127.0.0.1'))

    def authenticate(self, username):
        """Authenticates the given username by setting the appropriate cookies.

        .. note:: The database must contain a Voter object with a matching
                  username.
        """
        auth_policy = self.testapp.app.registry.queryUtility(IAuthenticationPolicy)
        request = testing.DummyRequest(environ=dict(
            REMOTE_ADDR='127.0.0.1',
            HTTP_HOST='127.0.0.1'))
        headers = auth_policy.remember(request, username)
        for _, cookie in headers:
            for key, morsel in SimpleCookie(cookie).items():
                self.testapp.cookies[key] = morsel.value

    def assertLogoutCookies(self, response):
        """Asserts that the given response contains the appropriate cookies
        to log out the user.
        """
        failed = True
        for header, value in response.headers.iteritems():
            if header.lower() == 'set-cookie':
                if value.startswith('auth_tkt'):
                    self.assertTrue('max-age=0' in value.lower(), value)
                    self.assertTrue('Expires=Wed, 31-Dec-97 23:59:59 GMT'.lower() in value.lower(), value)
                    failed = False

        if failed:
            self.fail('Failed to log out user')


class TestLogin(FunctionalTestCase):
    """Functional test for login."""

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 1, 1)))
    def test_login_forbidden_before_election_period(self):
        response = self.testapp.get('/tunnistaudu', expect_errors=True)
        self.assertEquals(response.status, '403 Forbidden')

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 3, 1, 12, 50)))
    def test_login_forbidden_after_election_period(self):
        response = self.testapp.get('/tunnistaudu', expect_errors=True)
        self.assertEquals(response.status, '403 Forbidden')

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 2, 15, 12, 50)))
    def test_login_allowed_during_election_period(self):
        response = self.testapp.get('/tunnistaudu')
        self.assertEquals(response.status, '200 OK')


class TestCandidateBrowsing(FunctionalTestCase):
    """Functional test for candidate browsing before elections."""

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 1, 1)))
    def test_browsing_allowed_before_election_period(self):
        response = self.testapp.get('/ehdokkaat')
        self.assertEquals(response.status, '200 OK')

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 2, 15, 12, 50)))
    def test_browsing_forbidden_during_election_period(self):
        response = self.testapp.get('/ehdokkaat', expect_errors=True)
        self.assertEquals(response.status, '403 Forbidden')

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 3, 1, 12, 50)))
    def test_browsing_forbidden_after_election_period(self):
        response = self.testapp.get('/ehdokkaat', expect_errors=True)
        self.assertEquals(response.status, '403 Forbidden')


class TestCandidateSelection(FunctionalTestCase):
    """Functional tests for candidate selection."""

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 1, 1)))
    def test_selection_forbidden_unauthorized_before_election_period(self):
        response = self.testapp.get('/valitse', expect_errors=True)
        self.assertEquals(response.status, '403 Forbidden')

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 1, 1)))
    def test_selection_forbidden_authorized_before_election_period(self):
        from nuvavaalit.models import Voter

        session = DBSession()
        session.add(Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers'))
        session.flush()

        self.authenticate(u'buck.rogers')
        response = self.testapp.get('/valitse', expect_errors=True)
        self.assertEquals(response.status, '403 Forbidden')

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 2, 15)))
    def test_already_voted_user_is_logged_out(self):
        from nuvavaalit.models import Voter
        from nuvavaalit.models import VotingLog

        session = DBSession()
        voter = Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers')
        session.add(voter)
        session.flush()
        session.add(VotingLog(voter))
        session.flush()

        self.assertTrue(voter.has_voted())
        self.authenticate(u'buck.rogers')
        response = self.testapp.get('/valitse')

        # An already voted user is redirected to the thank you page.
        self.assertEquals(response.status, '302 Found')
        self.assertEquals(response.location, 'http://localhost/kiitos')

        # Assert that we get cookies that log out the user.
        self.assertLogoutCookies(response)

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 2, 15)))
    def test_different_sessions_get_different_vote_links(self):
        from nuvavaalit.models import Candidate
        from nuvavaalit.models import Voter

        session = DBSession()
        session.add(Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers'))
        session.add(Candidate(2, u'Steven', u'Seagal', u'No pain, no game', u''))
        session.add(Candidate(7, u'Jet', u'Li', u'Yin, yang', u''))
        session.add(Candidate(11, u'Jean-Claude', u'van Damme', u'No engrish', u''))
        session.flush()

        response = self.testapp.get('/tunnistaudu')
        response.form['username'] = u'buck.rogers'
        response.form['password'] = u'secret'
        response = response.form.submit()

        self.assertEquals(response.status, '302 Found')
        self.assertEquals(response.location, 'http://localhost/valitse')
        response = response.follow()

        self.assertEquals(response.request.url, 'http://localhost/valitse')
        # Get a list of voting links
        voting_links = [str(tag) for tag in response.html.findAll('a', attrs={'href': re.compile('^http://localhost/aanesta/')})]

        # Login again to the application, creating a new session
        response = self.testapp.get('/tunnistaudu')
        response.form['username'] = u'buck.rogers'
        response.form['password'] = u'secret'
        response = response.form.submit()

        self.assertEquals(response.status, '302 Found')
        self.assertEquals(response.location, 'http://localhost/valitse')
        response = response.follow()

        self.assertEquals(response.request.url, 'http://localhost/valitse')
        new_voting_links = [str(tag) for tag in response.html.findAll('a', attrs={'href': re.compile('^http://localhost/aanesta/')})]

        self.assertEquals(len(voting_links), len(new_voting_links))
        self.assertNotEqual(voting_links, new_voting_links)

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 2, 15)))
    def test_encrypted_link_matches_selection(self):
        from nuvavaalit.models import Candidate
        from nuvavaalit.models import Voter

        session = DBSession()
        session.add(Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers'))
        session.add(Candidate(2, u'Steven', u'Seagal', u'No pain, no game', u''))
        session.add(Candidate(7, u'Jet', u'Li', u'Yin, yang', u''))
        session.add(Candidate(11, u'Jean-Claude', u'van Damme', u'No engrish', u''))
        session.flush()

        response = self.testapp.get('/tunnistaudu')
        response.form['username'] = u'buck.rogers'
        response.form['password'] = u'secret'
        response = response.form.submit()

        self.assertEquals(response.status, '302 Found')
        self.assertEquals(response.location, 'http://localhost/valitse')
        response = response.follow()

        self.assertEquals(response.request.url, 'http://localhost/valitse')
        voting_links = response.html.findAll('a', attrs={'href': re.compile('^http://localhost/aanesta/')})
        self.assertEquals(voting_links[1]['href'], voting_links[2]['href'])
        self.assertEquals(voting_links[2].text, u'Seagal, Steven, 2')
        # Click the voting link
        response = self.testapp.get(voting_links[2]['href'])
        # Assert that we get a matching candidate selection
        self.assertEquals(response.html.find('p', attrs={'class': 'candidate-name'}).text, u'2 Seagal, Steven')


class TestVoting(FunctionalTestCase):
    """Functional tests for the voting feature."""

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 1, 1)))
    def test_voting_forbidden_unauthorized_before_election_period(self):
        response = self.testapp.get('/aanesta/abcdefg', expect_errors=True)
        self.assertEquals(response.status, '403 Forbidden')

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 3, 1, 12, 50)))
    def test_voting_forbidden_unauthorized_after_election_period(self):
        response = self.testapp.get('/aanesta/abcdefg', expect_errors=True)
        self.assertEquals(response.status, '403 Forbidden')

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 1, 1)))
    def test_voting_forbidden_authorized_before_election_period(self):
        from nuvavaalit.models import Voter

        session = DBSession()
        session.add(Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers'))
        session.flush()

        self.authenticate(u'buck.rogers')
        response = self.testapp.get('/aanesta/abcdefg', expect_errors=True)
        self.assertEquals(response.status, '403 Forbidden')

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 3, 1, 12, 50)))
    def test_voting_forbidden_authorized_after_election_period(self):
        from nuvavaalit.models import Voter

        session = DBSession()
        session.add(Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers'))
        session.flush()

        self.authenticate(u'buck.rogers')
        response = self.testapp.get('/aanesta/abcdefg', expect_errors=True)
        self.assertEquals(response.status, '403 Forbidden')


class TestSuccessfulVotingProcess(FunctionalTestCase):
    """Exercises the system through a full successful voting process."""

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 2, 4, 12, 50)))
    def test_successful_voting_process(self):
        from nuvavaalit.models import Candidate
        from nuvavaalit.models import Vote
        from nuvavaalit.models import Voter
        from nuvavaalit.models import VotingLog

        # Create a user we will authenticate as.
        session = DBSession()
        session.add(Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers'))
        session.add(Candidate(2, u'Steven', u'Seägäl', u'No pain, no game', u''))
        session.add(Candidate(7, u'Jët', u'Li', u'Yin, yang', u''))
        session.add(Candidate(11, u'Jeän-Claüde', u'van Damme', u'No engrish', u''))
        session.flush()

        self.assertEquals(0, session.query(Vote).count())
        self.assertEquals(0, session.query(VotingLog).count())

        self.authenticate(u'buck.rogers')

        # Accessing the system front page will redirect us to the login page
        # during the elections.
        response = self.testapp.get('/')
        self.assertEquals(response.status, '302 Found')
        self.assertEquals(response.location, 'http://localhost/tunnistaudu')
        response = response.follow()

        # Logging in the system successfully will bring us to the candidate
        # selection page.
        response.form['username'] = u'buck.rogers'
        response.form['password'] = u'secret'
        response = response.form.submit()
        self.assertEquals(response.status, '302 Found')
        self.assertEquals(response.location, 'http://localhost/valitse')
        response = response.follow()

        # Selecting a candidate brings us to the voting page.
        self.assertEquals(response.request.url, 'http://localhost/valitse')
        voting_links = response.html.findAll('a', attrs={'href': re.compile('^http://localhost/aanesta/')})
        # Assert we have two links to the candidate.
        self.assertEquals(voting_links[1]['href'], voting_links[2]['href'])
        self.assertEquals(voting_links[2].text, u'Seägäl, Steven, 2')
        # Click the voting link
        response = self.testapp.get(voting_links[2]['href'])
        self.assertTrue(response.request.url.startswith('http://localhost/aanesta/'))
        # Assert that we get a matching candidate selection
        self.assertEquals(response.html.find('p', attrs={'class': 'candidate-name'}).text, u'2 Seägäl, Steven')

        # Attempting to vote a non-selected candidate gives us an error message.
        response.form['vote'] = u'69'
        response = response.form.submit()
        self.assertTrue(response.html.find('div', attrs={'class': 'error'}).text.startswith(u'Antamasi ehdokasnumero ei vastaa valintaasi'))
        self.assertTrue(response.request.url.startswith('http://localhost/aanesta/'))

        # Voting for the selected candidate stores the vote and logs out the user.
        response.form['vote'] = u'2'
        response = response.form.submit()
        self.assertEquals(response.status, '302 Found')
        self.assertEquals(response.location, 'http://localhost/kiitos')
        # Assert that we get cookies that log out the user.
        self.assertLogoutCookies(response)

        # Assert that the vote was recorded correctly.
        self.assertEquals(2, session.query(Vote).one().candidate.number)
        self.assertEquals(u'buck.rogers', session.query(VotingLog).one().voter.username)

        # Assert that subsequent attempts to login results in automatic logout.
        response = self.testapp.get('/tunnistaudu')
        response.form['username'] = u'buck.rogers'
        response.form['password'] = u'secret'
        response = response.form.submit()

        self.assertEquals(response.status, '302 Found')
        self.assertEquals(response.location, 'http://localhost/kiitos')
        # Assert that we get cookies that log out the user.
        self.assertLogoutCookies(response)
