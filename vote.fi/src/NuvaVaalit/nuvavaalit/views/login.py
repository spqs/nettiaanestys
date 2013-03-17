# -*- coding: utf-8 -*-
from nuvavaalit.crypto import session_key
from nuvavaalit.models import DBSession
from nuvavaalit.models import Voter
from nuvavaalit.views import disable_caching
from nuvavaalit.views import exit_voting
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.security import authenticated_userid
from pyramid.security import remember
from pyramid.url import route_url
from pyramid.view import view_config

import logging
import statsd


def authenticated_user(request):
    """Returns the currently authenticated user or `None`.

    :param request: The currently active request.
    :type request: :py:class:`pyramid.request.Request`

    :rtype: :py:class:`nuvavaalit.models.Voter` or ``None``
    """
    username = authenticated_userid(request)
    if username is not None:
        return DBSession().query(Voter).filter_by(username=username).first()


@view_config(route_name='login', renderer='templates/login.pt', permission='login')
def login(request):
    """Renders a login form and logs in a user if given the correct
    credentials.

    :param request: The currently active request.
    :type request: :py:class:`pyramid.request.Request`
    """
    session = DBSession()
    log = logging.getLogger('nuvavaalit')
    request.add_response_callback(disable_caching)
    error = None

    if 'form.submitted' in request.POST:
        username = request.POST['username']

        if request.session.get_csrf_token() != request.POST.get('csrf_token'):
            log.warn('CSRF attempt at {}.'.format(request.url))
            raise HTTPForbidden(u'CSRF attempt detected.')
        else:
            user = session.query(Voter).filter_by(username=username).first()
            password = request.POST['password']

            if user is not None and user.check_password(password):
                if user.has_voted():
                    log.warn('User {} attempted to log in after already voting.'.format(user.username))
                    if request.statsd:
                        statsd.increment('login.voted')
                    return exit_voting(request)
                else:
                    headers = remember(request, user.username)
                    # Generate an encryption key for the duration of the session.
                    request.session['encryption_key'] = session_key()
                    log.info('Successful login for "{}".'.format(user.username))
                    if request.statsd:
                        statsd.increment('login.success')
                    return HTTPFound(location=route_url('select', request), headers=headers)

            error = u'Tunnistautuminen epäonnistui. Kokeile tunnistautua uudelleen!'
            if request.statsd:
                statsd.increment('login.failure')
            log.warn('Failed login attempt for {}'.format(request.POST.get('username').encode('utf-8')))

    return {
        'action_url': route_url('login', request),
        'csrf_token': request.session.get_csrf_token(),
        'error': error,
    }
