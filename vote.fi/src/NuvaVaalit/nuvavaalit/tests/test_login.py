# -*- coding: utf-8 -*-
from datetime import datetime
from nuvavaalit.models import DBSession
from nuvavaalit.tests import election_period
from nuvavaalit.tests import init_testing_db
from nuvavaalit.tests import static_datetime
from pyramid import testing
from pyramid.httpexceptions import HTTPForbidden
import mock
import unittest


class TestUtilities(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()
        DBSession.remove()

    def test_authenticated_user__anonymous(self):
        from nuvavaalit.views.login import authenticated_user

        request = testing.DummyRequest(statsd=False)
        self.assertTrue(authenticated_user(request) is None)

    def test_authenticated_user__authenticated(self):
        from nuvavaalit.models import Voter
        from nuvavaalit.views.login import authenticated_user

        self.config.testing_securitypolicy(userid=u'buck.rogers')
        session = DBSession()

        user = Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers')
        session.add(user)

        self.assertEquals(user, authenticated_user(testing.DummyRequest(statsd=False)))

    def test_authenticated_user__authenticated_model_missing(self):
        from nuvavaalit.views.login import authenticated_user

        self.config.testing_securitypolicy(userid=u'buck.rogers')
        self.assertTrue(authenticated_user(testing.DummyRequest(statsd=False)) is None)


class TestLoginView(unittest.TestCase):

    def setUp(self):
        from pyramid.session import UnencryptedCookieSessionFactoryConfig
        self.config = testing.setUp()
        self.config.add_route('select', 'valitse')
        self.config.add_route('login', 'tunnistaudu')
        self.config.set_session_factory(UnencryptedCookieSessionFactoryConfig)
        self.config.add_settings({
            'nuvavaalit.election_period': election_period(
                datetime(2011, 2, 1), datetime(2011, 3, 1)),
        })
        init_testing_db()

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 2, 15)))
    def test_login__no_submission(self):
        from nuvavaalit.views.login import login
        request = testing.DummyRequest(statsd=False)
        token = request.session.new_csrf_token()

        options = login(request)
        self.assertEquals(options, {
            'action_url': 'http://example.com/tunnistaudu',
            'csrf_token': token,
            'error': None})

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 2, 15)))
    def test_login__form_submission__non_existing_user(self):
        from nuvavaalit.views.login import login
        request = testing.DummyRequest(statsd=False)
        token = request.session.new_csrf_token()
        request.POST = {
            'form.submitted': u'1',
            'username': u'john.doe',
            'password': u'thisiswrong',
            'csrf_token': token,
        }

        options = login(request)
        self.assertEquals(options, {
            'action_url': 'http://example.com/tunnistaudu',
            'csrf_token': token,
            'error': u'Tunnistautuminen epäonnistui. Kokeile tunnistautua uudelleen!'})

    def test_login__form_submission__csrf_mismatch(self):
        from nuvavaalit.views.login import login

        request = testing.DummyRequest(statsd=False)
        token = request.session.new_csrf_token()
        request.POST = {
            'form.submitted': u'1',
            'username': u'john.doe',
            'password': u'thisiswrong',
            'csrf_token': u'invalid',
        }

        self.assertFalse(token == u'invalid')
        self.assertRaises(HTTPForbidden, lambda: login(request))

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 2, 15)))
    def test_login__form_submission__invalid_password(self):
        from nuvavaalit.models import Voter
        from nuvavaalit.views.login import login

        session = DBSession()
        session.add(Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers'))
        session.flush()
        self.assertEquals(
            session.query(Voter).filter_by(username=u'buck.rogers').first().fullname(),
            u'Bück Rögers')

        request = testing.DummyRequest(statsd=False)
        token = request.session.new_csrf_token()
        request.POST = {
            'form.submitted': u'1',
            'username': u'buck.rogers',
            'password': u'thisiswrong',
            'csrf_token': token,
        }

        options = login(request)
        self.assertEquals(options, {
            'action_url': 'http://example.com/tunnistaudu',
            'csrf_token': token,
            'error': u'Tunnistautuminen epäonnistui. Kokeile tunnistautua uudelleen!'})

    @mock.patch('nuvavaalit.models.datetime', static_datetime(datetime(2011, 2, 15)))
    @mock.patch('nuvavaalit.views.login.remember')
    def test_login__form_submission__success(self, remember):
        from nuvavaalit.models import Voter
        from nuvavaalit.views.login import login

        session = DBSession()
        session.add(Voter(u'buck.rogers', u'secret', u'Bück', u'Rögers'))
        session.flush()
        self.assertEquals(
            session.query(Voter).filter_by(username=u'buck.rogers').first().fullname(),
            u'Bück Rögers')

        remember.return_value = [('X-Login', 'buck.rogers')]
        request = testing.DummyRequest(statsd=False)
        token = request.session.new_csrf_token()
        request.POST = {
            'form.submitted': u'1',
            'username': u'buck.rogers',
            'password': u'secret',
            'csrf_token': token,
        }

        response = login(request)
        self.assertEquals(dict(response.headers), {
            'Content-Length': '0',
            'Content-Type': 'text/html; charset=UTF-8',
            'Location': 'http://example.com/valitse',
            'X-Login': 'buck.rogers'})
