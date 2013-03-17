# -*- coding: utf-8 -*-
from datetime import datetime
from sqlalchemy import create_engine


def static_datetime(static_datetime):
    """Returns a modified ``datetime.datetime`` class with a static .now()
    method which returns the given ``date`` which must be an instance of
    ``datetime.datetime``."""
    if not isinstance(static_datetime, datetime):
        raise TypeError('The static datetime must be an instance of datetime.datetime.')

    class StaticNow(datetime):
        @classmethod
        def now(cls, *args, **kwargs):
            return static_datetime

    return StaticNow


def election_period(start, end, fmt='%Y-%m-%d %H:%M'):
    """Creates an election period configuration value.

    :param start: The beginning of the election period.
    :type start: `datetime.datetime'

    :param end: The end of the election period.
    :type end: `datetime.datetime`

    :param fmt: Date format string.
    :type fmt: str

    :returns: Election period configuration value.
    :rtype: str
    """
    return '\n'.join([start.strftime(fmt), end.strftime(fmt)])


def init_testing_db(echo=False):
    from nuvavaalit.models import initialize_sql
    import warnings

    #warnings.simplefilter('error')
    engine = create_engine('sqlite:///', echo=echo)
    session = initialize_sql(engine)
    return session
