from collections import defaultdict
from nuvavaalit.models import Candidate
from nuvavaalit.models import DBSession
from nuvavaalit.models import Vote
from nuvavaalit.models import Voter
from pyramid.settings import asbool
from pyramid.view import view_config
from sqlalchemy import func
import hashlib


def sort_hash(*items):
    """Returns a salted hash calculated over the given items.

    :param items: Iterable of opaque data items to hash.
    :type items: iter

    :rtype: str
    """
    def bytes(o):
        return item.encode('utf-8') if isinstance(o, unicode) else str(o)

    h = hashlib.sha1('f6676aad6a9c04a9c2483c7e13f66c1bfe3a1072dbb337e754716577f950de3a')
    for item in items:
        h.update(bytes(item))
    return h.digest()


def format_percentage(count, total):
    """Renders a percentage value of count / total.

    The percentage will be set to ``'0.0'`` if `total` is zero.

    :param count: The number of occurrences.
    :type count: int

    :param total: The total size of the possible occurrencies.
    :type total: int

    :rtype: str
    """
    if total == 0:
        return '0.0'

    return '{:0.1f}'.format((count / float(total)) * 100)


@view_config(route_name='results', renderer='templates/results.pt', permission='results')
def results(request):
    """Calculates the results of the election.
    """
    session = DBSession()
    votes = defaultdict(int)

    # TODO: Merge the following two queries into a single outer join to calculate the votes.
    votes.update(dict(session.query(Vote.candidate_id, func.COUNT(Vote.candidate_id))\
                        .group_by(Vote.candidate_id).all()))

    total_votes = float(sum(votes.values()))
    results = []
    for candidate in session.query(Candidate):
        if not candidate.is_empty():
            results.append({
                'name': candidate.fullname(),
                'number': candidate.number,
                'votes': votes[candidate.id],
                'percentage': format_percentage(votes[candidate.id], total_votes),
            })

    # Sort the list of results so that equal votes are ordered in
    # random but stable ordering.
    results.sort(
        key=lambda r: (r['votes'], sort_hash(r['name'], r['number'])),
        reverse=True)

    voting_percentage = format_percentage(
        session.query(func.COUNT(Vote.id)).scalar(), session.query(func.COUNT(Voter.id)).scalar())
    threshold = int(request.registry.settings['nuvavaalit.num_selected_candidates'].strip())

    return {
        'selected': results[:threshold],
        'others': results[threshold:],
        'voting_percentage': voting_percentage,
        'total_votes': int(total_votes),
        'threshold': threshold,
        'show_leftovers': asbool(request.registry.settings.get('nuvavaalit.show_all_results', 'false')),
    }
