from itertools import cycle
from nuvavaalit.models import Candidate
from nuvavaalit.models import DBSession
from nuvavaalit.models import Schedule
from pyramid.httpexceptions import HTTPFound
from pyramid.url import route_url
from pyramid.view import view_config


def split_candidates(candidates, columns):
    """Splits a list of candidates to be rendered in a number of columns.

    Columns are filled from left to right so a previous column will always
    contain more or equal amount of candidates.

    :param candidates: An iterable of candidates that will be split.
    :type candidates: iterable

    :param columns: The number of columns to split the candidates in.
    :type columns: int

    :rtype: generator
    """
    size = len(candidates)
    offset = 0
    while offset < size:
        yield candidates[offset:(offset + columns)]
        offset += columns


@view_config(route_name='browse_candidates', renderer='templates/browse_candidates.pt', permission='browse')
def browse_candidates(request):
    """Renders a listing of candidates prior to the election.

    This is a read-only page which does not allow voting. The main purpose is
    to allow voters to familiarize themselves with the candidates prior to the
    election.

    :param request: The currently active request.
    :type request: :py:class:`pyramid.request.Request`

    :rtype: dict
    """
    session = DBSession()
    query = session.query(Candidate)\
                .filter(Candidate.number != Candidate.EMPTY_CANDIDATE)\
                .order_by(Candidate.number)
    positions = '0 1:3 2:3'.split()

    candidates = []
    for candidate in query.all():
        candidates.append({
            'name': candidate.fullname(),
            'number': candidate.number,
            'slogan': candidate.slogan,
            'image_url': request.static_url('nuvavaalit:views/templates/static/images/candidates/{}.jpg'.format(candidate.number)),
            })

    return {
        'candidates': split_candidates(candidates, len(positions)),
        'positions': cycle(positions),
        'columns': len(positions),
        'page_name': 'browse',
    }


@view_config(route_name='home', renderer='templates/home.pt')
def home(request):
    """Entry page."""
    schedule = Schedule(request)

    if schedule.during_elections():
        # During the election period the front page will redirect to the
        # authentication page.
        return HTTPFound(location=route_url('login', request))
    elif schedule.after_elections():
        # After the elections the front page will redirect to the results page.
        return HTTPFound(location=route_url('results', request))

    return {
        'browse_url': route_url('browse_candidates', request)
    }
