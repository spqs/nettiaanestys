# -*- coding: utf-8 -*-
from datetime import datetime
from nuvavaalit.models import DBSession
from nuvavaalit.tests import election_period
from nuvavaalit.tests import init_testing_db

from pyramid import testing
from pyramid.httpexceptions import HTTPForbidden
import mock
import unittest


class TestCandidateSelection(unittest.TestCase):
    """Tests for the candiate selection view."""

    maxDiff = None

    def setUp(self):
        from pyramid.session import UnencryptedCookieSessionFactoryConfig
        self.config = testing.setUp()
        self.config.add_route('vote', '/aanesta/{id}')
        self.config.add_route('thanks', '/kiitos')
        self.config.set_session_factory(UnencryptedCookieSessionFactoryConfig)
        self.config.add_static_view('static', 'nuvavaalit:views/templates/static')
        self.config.add_settings({
            'nuvavaalit.election_period': election_period(
                datetime(2011, 2, 1), datetime(2011, 3, 1)),
        })
        init_testing_db()

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def test_forbidden_for_unauthorized(self):
        from nuvavaalit.views.voting import select

        self.assertRaises(HTTPForbidden, lambda: select(testing.DummyRequest(statsd=False)))

    def test_redirect_already_voted(self):
        from nuvavaalit.models import Voter
        from nuvavaalit.models import VotingLog
        from nuvavaalit.views.voting import select

        # Create an authenticated user
        session = DBSession()
        voter = Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers')
        session.add(voter)
        session.flush()
        session.add(VotingLog(voter))
        session.flush()
        self.assertTrue(voter.has_voted())

        self.config.testing_securitypolicy(userid=u'buck.rogers')
        request = testing.DummyRequest(statsd=False)
        request.session['encryption_key'] = 'secret'
        response = select(request)

        self.assertEquals(response.status, '302 Found')
        self.assertEquals(response.location, 'http://example.com/kiitos')

    @mock.patch('nuvavaalit.crypto.generate_iv')
    def test_select_candidates(self, generate_iv):
        from itertools import cycle
        from nuvavaalit.models import Candidate
        from nuvavaalit.models import Voter
        from nuvavaalit.views.voting import select

        session = DBSession()
        session.add(Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers'))
        session.add(Candidate(2, u'Steven', u'Seagal', u'No pain, no game', u''))
        session.add(Candidate(7, u'Jet', u'Li', u'Yin, yang', u''))
        session.add(Candidate(11, u'Jean-Claude', u'van Damme', u'No engrish', u''))
        session.flush()

        self.config.testing_securitypolicy(userid=u'buck.rogers')
        request = testing.DummyRequest(statsd=False)

        # Make the encryption predictable by using static values for the IV and
        # the session key.
        request.session['encryption_key'] = 'secretsessionkeyforcandidatenumbers'
        generate_iv.return_value = 'abcdefghijklmnop'
        options = select(request)

        # Remove the generator for the options
        self.assertTrue(isinstance(options.pop('positions'), cycle))
        self.assertEquals(list(options.pop('candidates')), [
            [{'image_url': 'http://example.com/static/images/candidates/2.jpg',
              'name': u'Seagal, Steven',
              'number': 2,
              'vote_url': 'http://example.com/aanesta/6162636465666768696a6b6c6d6e6f709e'},
             {'image_url': 'http://example.com/static/images/candidates/7.jpg',
              'name': u'Li, Jet',
              'number': 7,
              'vote_url': 'http://example.com/aanesta/6162636465666768696a6b6c6d6e6f709b'},
             {'image_url': 'http://example.com/static/images/candidates/11.jpg',
              'name': u'van Damme, Jean-Claude',
              'number': 11,
              'vote_url': 'http://example.com/aanesta/6162636465666768696a6b6c6d6e6f709d88'}]])
        self.assertEquals(options, {
            'columns': 3,
            'empty_vote_number': 0,
            'empty_vote_url': 'http://example.com/aanesta/6162636465666768696a6b6c6d6e6f709c'})


class TestVoting(unittest.TestCase):
    """Tests for the voting view."""

    maxDiff = None

    def setUp(self):
        from pyramid.session import UnencryptedCookieSessionFactoryConfig
        self.config = testing.setUp()
        self.config.add_route('select', '/valitse')
        self.config.add_route('thanks', '/kiitos')
        self.config.set_session_factory(UnencryptedCookieSessionFactoryConfig)
        self.config.add_static_view('static', 'nuvavaalit:views/templates/static')
        self.config.add_settings({
            'nuvavaalit.election_period': election_period(
                datetime(2011, 2, 1), datetime(2011, 3, 1)),
        })
        init_testing_db()

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def test_forbidden_for_unauthorized(self):
        from nuvavaalit.views.voting import vote

        self.assertRaises(HTTPForbidden, lambda: vote(testing.DummyRequest(statsd=False)))

    def test_redirect_already_voted(self):
        from nuvavaalit.models import Voter
        from nuvavaalit.models import VotingLog
        from nuvavaalit.views.voting import vote

        # Create an authenticated user
        session = DBSession()
        voter = Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers')
        session.add(voter)
        session.flush()
        session.add(VotingLog(voter))
        session.flush()
        self.assertTrue(voter.has_voted())

        self.config.testing_securitypolicy(userid=u'buck.rogers')
        request = testing.DummyRequest(statsd=False)
        request.session['encryption_key'] = 'secret'
        response = vote(request)

        self.assertEquals(response.status, '302 Found')
        self.assertEquals(response.location, 'http://example.com/kiitos')

    def test_encrypted_candidate_is_invalid(self):
        from nuvavaalit.models import Voter
        from nuvavaalit.views.voting import vote
        from pyramid.httpexceptions import HTTPNotFound

        # Create an authenticated user
        session = DBSession()
        voter = Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers')
        session.add(voter)
        session.flush()
        self.assertFalse(voter.has_voted())
        self.config.testing_securitypolicy(userid=u'buck.rogers')

        request = testing.DummyRequest(statsd=False)
        request.session['encryption_key'] = 'secret'
        request.matchdict['id'] = 'garbage'

        self.assertRaises(HTTPNotFound, lambda: vote(request))

    def test_candidate_does_not_exist(self):
        from nuvavaalit.crypto import decrypt
        from nuvavaalit.crypto import encrypt
        from nuvavaalit.models import Voter
        from nuvavaalit.views.voting import vote
        from pyramid.httpexceptions import HTTPNotFound

        # Create an authenticated user
        session = DBSession()
        voter = Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers')
        session.add(voter)
        session.flush()
        self.assertFalse(voter.has_voted())
        self.config.testing_securitypolicy(userid=u'buck.rogers')

        request = testing.DummyRequest(statsd=False)
        request.session['encryption_key'] = 'secret'
        request.matchdict['id'] = encrypt('69', request.session['encryption_key'])

        self.assertEquals(69, int(decrypt(request.matchdict['id'], request.session['encryption_key'])))
        self.assertRaises(HTTPNotFound, lambda: vote(request))

    def test_entry_to_voting_page(self):
        from nuvavaalit.crypto import decrypt
        from nuvavaalit.crypto import encrypt
        from nuvavaalit.models import Candidate
        from nuvavaalit.models import Voter
        from nuvavaalit.views.voting import vote

        # Create an authenticated user
        session = DBSession()
        voter = Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers')
        session.add(voter)
        session.add(Candidate(2, u'Steven', u'Seagal', u'No pain, no game', u''))
        session.add(Candidate(7, u'Jet', u'Li', u'Yin, yang', u''))
        session.add(Candidate(11, u'Jean-Claude', u'van Damme', u'No engrish', u''))
        session.flush()
        self.assertFalse(voter.has_voted())
        self.config.testing_securitypolicy(userid=u'buck.rogers')

        request = testing.DummyRequest(statsd=False)
        request.session['encryption_key'] = 'secret'
        request.matchdict['id'] = encrypt('7', request.session['encryption_key'])
        token = request.session.new_csrf_token()

        self.assertEquals(7, int(decrypt(request.matchdict['id'], request.session['encryption_key'])))
        self.assertEquals(vote(request), {
            'action_url': 'http://example.com',
            'candidate': {'name': u'Li, Jet', 'number': 7},
            'csrf_token': token,
            'error': False,
            'unload_confirmation': u'Et ole vielä äänestänyt. Oletko varma, että haluat poistua sivulta?',
            'select_url': 'http://example.com/valitse',
            'voter': {'fullname': u'Bück Rögers'}})

    def test_vote_with_csrf_failure(self):
        from nuvavaalit.crypto import decrypt
        from nuvavaalit.crypto import encrypt
        from nuvavaalit.models import Candidate
        from nuvavaalit.models import Voter
        from nuvavaalit.views.voting import vote

        # Create an authenticated user
        session = DBSession()
        voter = Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers')
        session.add(voter)
        session.add(Candidate(2, u'Steven', u'Seagal', u'No pain, no game', u''))
        session.add(Candidate(7, u'Jet', u'Li', u'Yin, yang', u''))
        session.add(Candidate(11, u'Jean-Claude', u'van Damme', u'No engrish', u''))
        session.flush()
        self.assertFalse(voter.has_voted())
        self.config.testing_securitypolicy(userid=u'buck.rogers')

        request = testing.DummyRequest(statsd=False)
        request.session['encryption_key'] = 'secret'
        request.matchdict['id'] = encrypt('7', request.session['encryption_key'])
        request.POST.update({
            'csrf_token': 'invalid_csfr_token',
            'vote': '1',
        })
        token = request.session.new_csrf_token()

        # Sanity checks
        self.assertNotEqual(request.POST['csrf_token'], token)
        self.assertEquals(7, int(decrypt(request.matchdict['id'], request.session['encryption_key'])))
        # Assert CSRF check
        self.assertEquals(vote(request), {
            'action_url': 'http://example.com',
            'candidate': {'name': u'Li, Jet', 'number': 7},
            'csrf_token': token,
            'error': True,
            'unload_confirmation': u'Et ole vielä äänestänyt. Oletko varma, että haluat poistua sivulta?',
            'select_url': 'http://example.com/valitse',
            'voter': {'fullname': u'Bück Rögers'}})

    def test_vote_with_wrong_candidate_number(self):
        from nuvavaalit.crypto import decrypt
        from nuvavaalit.crypto import encrypt
        from nuvavaalit.models import Candidate
        from nuvavaalit.models import Voter
        from nuvavaalit.views.voting import vote

        # Create an authenticated user
        session = DBSession()
        voter = Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers')
        session.add(voter)
        session.add(Candidate(2, u'Steven', u'Seagal', u'No pain, no game', u''))
        session.add(Candidate(7, u'Jet', u'Li', u'Yin, yang', u''))
        session.add(Candidate(11, u'Jean-Claude', u'van Damme', u'No engrish', u''))
        session.flush()
        self.assertFalse(voter.has_voted())
        self.config.testing_securitypolicy(userid=u'buck.rogers')

        request = testing.DummyRequest(statsd=False)
        token = request.session.new_csrf_token()
        request.session['encryption_key'] = 'secret'
        request.matchdict['id'] = encrypt('7', request.session['encryption_key'])
        request.POST.update({
            'csrf_token': token,
            'vote': '2',  # The vote is for a candidate which does not match the matchdict.
        })

        # Sanity checks
        self.assertEquals(7, int(decrypt(request.matchdict['id'], request.session['encryption_key'])))
        # Assert error check
        self.assertEquals(vote(request), {
            'action_url': 'http://example.com',
            'candidate': {'name': u'Li, Jet', 'number': 7},
            'csrf_token': token,
            'error': True,
            'unload_confirmation': u'Et ole vielä äänestänyt. Oletko varma, että haluat poistua sivulta?',
            'select_url': 'http://example.com/valitse',
            'voter': {'fullname': u'Bück Rögers'}})

    def test_successful_vote(self):
        from nuvavaalit.crypto import decrypt
        from nuvavaalit.crypto import encrypt
        from nuvavaalit.models import Candidate
        from nuvavaalit.models import Vote
        from nuvavaalit.models import Voter
        from nuvavaalit.models import VotingLog
        from nuvavaalit.views.voting import vote

        # Create an authenticated user
        session = DBSession()
        voter = Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers')
        session.add(voter)
        session.add(Candidate(2, u'Steven', u'Seagal', u'No pain, no game', u''))
        session.add(Candidate(7, u'Jet', u'Li', u'Yin, yang', u''))
        session.add(Candidate(11, u'Jean-Claude', u'van Damme', u'No engrish', u''))
        session.flush()
        self.assertFalse(voter.has_voted())
        self.config.testing_securitypolicy(userid=u'buck.rogers')

        request = testing.DummyRequest(statsd=False)
        token = request.session.new_csrf_token()
        request.session['encryption_key'] = 'secret'
        request.matchdict['id'] = encrypt('7', request.session['encryption_key'])
        request.POST.update({
            'csrf_token': token,
            'vote': '7',
        })

        # Sanity checks
        self.assertEquals(7, int(decrypt(request.matchdict['id'], request.session['encryption_key'])))
        self.assertEquals(session.query(Vote).count(), 0)
        self.assertEquals(session.query(VotingLog).count(), 0)

        response = vote(request)
        # Assert that the user is redirected to the thank you page
        self.assertEquals(response.status, '302 Found')
        self.assertEquals(response.location, 'http://example.com/kiitos')
        # Assert that the vote was correctly recorded.
        self.assertEquals(session.query(Vote).one().candidate.number, 7)
        self.assertEquals(session.query(VotingLog).one().voter.username, u'buck.rogers')

    def test_thanks_page(self):
        from nuvavaalit.views.voting import thanks

        self.assertEquals({}, thanks(testing.DummyRequest(statsd=False)))
