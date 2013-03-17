from pyramid.testing import DummyRequest

import unittest


class TestHelpers(unittest.TestCase):

    def test_static_datetime(self):
        from datetime import datetime
        from nuvavaalit.tests import static_datetime

        d = datetime(1999, 1, 2, 3, 4, 5, 6)
        static = static_datetime(d)
        for i in xrange(1000):
            self.assertEquals(d, static.now())

    def test_static_datetime__invalid(self):
        from nuvavaalit.tests import static_datetime

        self.assertRaises(TypeError, lambda: static_datetime(None))
        self.assertRaises(TypeError, lambda: static_datetime(u'Invalid'))


class TestSystem(unittest.TestCase):

    def test_ping(self):
        from nuvavaalit.views.system import ping

        response = ping(DummyRequest(statsd=False))
        self.assertEquals(response.status, '200 OK')
        self.assertEquals(response.body, 'pong')

    def test_forbidden(self):
        from nuvavaalit.views.system import forbidden

        request = DummyRequest(statsd=False)
        response = forbidden(request)
        self.assertEquals(response, {})
        self.assertEquals(request.response.status, '403 Forbidden')

    def test_notfound(self):
        from nuvavaalit.views.system import notfound

        request = DummyRequest(statsd=False)
        response = notfound(request)
        self.assertEquals(response, {})
        self.assertEquals(request.response.status, '404 Not Found')
