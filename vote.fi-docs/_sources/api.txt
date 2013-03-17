API documentation
=================

Database models
---------------

.. automodule:: nuvavaalit.models
.. moduleauthor:: Hexagon IT <info@hexagonit.fi>

.. autoclass:: Schedule
    :members:

.. autoclass:: RootFactory
    :members:

.. autoclass:: Candidate
    :members:

.. autoclass:: Voter
    :members:

.. autoclass:: Vote
    :members:

    .. py:attribute:: candidate

      Reference to an associated :py:class:`Candidate` object or ``None``. This
      is created as a backreference in the :py:attr:`Candidate.votes`
      relationship.

.. autoclass:: VotingLog
    :members:


Event subscribers
-----------------

.. automodule:: nuvavaalit.events

.. autofunction:: renderer_globals

.. autofunction:: new_request


Cryptographic utilities
-----------------------

.. automodule:: nuvavaalit.crypto

.. autofunction:: encrypt

.. autofunction:: decrypt

.. autofunction:: session_key

.. autofunction:: generate_iv

Public views
------------

.. automodule:: nuvavaalit.views.login

.. autofunction:: login

.. automodule:: nuvavaalit.views.public

.. autofunction:: home

.. autofunction:: browse_candidates

Voting views
------------

.. automodule:: nuvavaalit.views.voting

.. autofunction:: select

.. autofunction:: vote

.. autofunction:: thanks

.. automodule:: nuvavaalit.views.results

.. autofunction:: results

Utilities
---------

.. automodule:: nuvavaalit.views

.. autofunction:: disable_caching

.. autofunction:: exit_voting


.. currentmodule:: nuvavaalit.views.login

.. autofunction:: authenticated_user


.. currentmodule:: nuvavaalit.views.results

.. autofunction:: sort_hash

.. autofunction:: format_percentage
