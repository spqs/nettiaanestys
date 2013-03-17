# -*- coding: utf-8 -*-
from itertools import cycle
from nuvavaalit.crypto import decrypt
from nuvavaalit.crypto import encrypt
from nuvavaalit.i18n import _
from nuvavaalit.models import Candidate
from nuvavaalit.models import DBSession
from nuvavaalit.models import Vote
from nuvavaalit.models import VotingLog
from nuvavaalit.views import disable_caching
from nuvavaalit.views import exit_voting
from nuvavaalit.views.login import authenticated_user
from nuvavaalit.views.public import split_candidates
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPNotFound
from pyramid.i18n import get_localizer
from pyramid.url import route_url
from pyramid.view import view_config

import logging
import statsd


@view_config(route_name='select', renderer='templates/select.pt', permission='vote')
def select(request):
    """Renders the candidate selection list.

    The link to the voting page for each candidate contains an identifier
    which is the result of encrypting the candidate number with a random
    session key. The main benefit from this is that the chosen candidate can
    not be identified from the used URL. This allows us to use GET requests
    instead of POST requests without having to worry about leaking information
    in server logs and browser history.

    :param request: The currently active request.
    :type request: :py:class:`pyramid.request.Request`

    :rtype: dict
    """
    # Deco Grid positions for the candidate columns.
    positions = '0 1:3 2:3'.split()
    session = DBSession()
    log = logging.getLogger('nuvavaalit')
    # Disable caching
    request.add_response_callback(disable_caching)

    # Require authentication.
    voter = authenticated_user(request)
    if voter is None:
        log.warn('Unauthenticated attempt to select candidates.')
        raise HTTPForbidden()

    # User should vote only once.
    if voter.has_voted():
        log.warn('User "{}" attempted to select candidates after voting.'.format(voter.username))
        return exit_voting(request)

    query = session.query(Candidate)\
                .filter(Candidate.number != Candidate.EMPTY_CANDIDATE)\
                .order_by(Candidate.number)

    candidates = []
    for candidate in query.all():
        candidates.append({
            'name': candidate.fullname(),
            'number': candidate.number,
            'vote_url': route_url('vote', request, id=encrypt(str(candidate.number), request.session['encryption_key'])),
            'image_url': request.static_url('nuvavaalit:views/templates/static/images/candidates/{}.jpg'.format(candidate.number)),
        })

    return {
        'candidates': split_candidates(candidates, len(positions)),
        'positions': cycle(positions),
        'columns': len(positions),
        'empty_vote_url': route_url('vote', request, id=encrypt(str(Candidate.EMPTY_CANDIDATE), request.session['encryption_key'])),
        'empty_vote_number': Candidate.EMPTY_CANDIDATE,
    }


@view_config(route_name='vote', renderer='templates/vote.pt', permission='vote')
def vote(request):
    """Renders the voting form for the selected candidate and processes the
    vote.

    A valid vote must meet all of the following criteria:

        * The voter must be authenticated.

        * The voter must not have voted previously.

        * The candidate must be the one chosen in the previous step (See
          :py:func:`select`).

        * The CSRF token included in the form must be valid.

    :param request: The currently active request.
    :type request: :py:class:`pyramid.request.Request`

    :rtype: dict
    """
    error = False
    session = DBSession()
    voter = authenticated_user(request)
    log = logging.getLogger('nuvavaalit')
    request.add_response_callback(disable_caching)
    localizer = get_localizer(request)

    # The user must be authenticated at this time
    if voter is None:
        log.warn('Unauthenticated attempt to vote.')
        raise HTTPForbidden()

    # The user may vote only once
    if voter.has_voted():
        log.warn('User "{}" attempted to vote a second time.'.format(voter.username))
        return exit_voting(request)

    # Find the selected candidate
    try:
        number = int(decrypt(request.matchdict['id'], request.session['encryption_key']))
    except (ValueError, TypeError):
        log.warn('Candidate number decryption failed')
        raise HTTPNotFound

    candidate = session.query(Candidate)\
            .filter(Candidate.number == number)\
            .first()

    if candidate is None:
        log.warn('User "{}" attempted to vote for a non-existing candidate "{}".'.format(
            voter.username, number))
        raise HTTPNotFound

    # Handle voting
    if 'vote' in request.POST:

        if request.session.get_csrf_token() != request.POST.get('csrf_token'):
            log.warn('CSRF attempt at: {0}.'.format(request.url))
            error = True
        elif request.POST['vote'].strip() == str(number):

            session.add(Vote(candidate))
            session.add(VotingLog(voter))

            log.info('Stored vote cast by "{}".'.format(voter.username))
            if request.statsd:
                statsd.increment('vote.success')
            return exit_voting(request)
        else:
            error = True

    if request.statsd and error:
        statsd.increment('vote.error')

    options = {
        'action_url': request.path_url,
        'select_url': route_url('select', request),
        'candidate': {
            'number': candidate.number,
            'name': candidate.fullname() if not candidate.is_empty() else _(u'Tyhjä'),
            },
        'voter': {
            'fullname': voter.fullname(),
        },
        'error': error,
        'csrf_token': request.session.get_csrf_token(),
        'unload_confirmation': localizer.translate(
            _(u'Et ole vielä äänestänyt. Oletko varma, että haluat poistua sivulta?')),
    }

    return options


@view_config(route_name='thanks', renderer='templates/thanks.pt')
def thanks(request):
    """The final page after voting.

    At this time the user has already been logged out.

    :param request: The currently active request.
    :type request: :py:class:`pyramid.request.Request`

    :rtype: dict
    """
    return {}
