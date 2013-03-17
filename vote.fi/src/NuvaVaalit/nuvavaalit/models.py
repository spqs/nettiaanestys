from datetime import datetime
from pyramid.security import Allow
from pyramid.security import Authenticated
from pyramid.security import Everyone
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Unicode
from sqlalchemy import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import synonym
from z3c.bcrypt import BcryptPasswordManager
from zope.sqlalchemy import ZopeTransactionExtension
import time

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()
password_manager = BcryptPasswordManager()


class Schedule(object):
    """Election schedule.

    From the point of view of the election there are three distinct time
    periods: the time before the election, the time during the election and
    the time after the election.

    Voting is allowed only during the election, results will be available only
    after the election and so on. This class provides an abstraction for the
    application to determine which is the current time period.

    The election period should be configured in the associated .ini
    configuration using a ``nuvavaalit.election_period`` option within the
    application configuration section. The option must consist of two (newline
    separated) formatted timestamps which define the start and end of the
    voting election. The format of the timestamps is ``%Y-%m-%d %H:%M``
    """

    def __init__(self, request):
        """Constructor.

        :param request: The currently active request:
        :type request: `pyramid.request.Request`

        :raises: `ValueError`, if the election period is not correctly defined.
        """
        try:
            start, end = [
                datetime.strptime(d.strip(), '%Y-%m-%d %H:%M')
                for d in request.registry.settings.get(
                    'nuvavaalit.election_period', '').strip().splitlines()[:2]]
            if start >= end:
                raise ValueError

            self.start = start
            self.end = end
        except ValueError:
            raise ValueError('Invalid election period configuration (nuvavaalit.election_period)')

    def before_elections(self):
        """Checks if we are currently in a time period before the elections.

        :return: `True`, if the elections are in the future, `False` otherwise.
        :rtype: bool
        """
        return self.start > datetime.now()

    def after_elections(self):
        """Checks if we are currently in a time period after the elections.

        :return: `True`, if the elections are in the past, `False` otherwise.
        :rtype: bool
        """
        return self.end < datetime.now()

    def during_elections(self):
        """Checks if the elections are active currently.

        :return: `True`, if the elections are in the future, `False` otherwise.
        :rtype: bool
        """
        return self.start < datetime.now() < self.end


class RootFactory(object):
    """Custom root factory.

    An instance of this class will function as the context for all views. The
    instance implements the access control policy which has the following
    rules
    """

    def __init__(self, request):
        if getattr(request, 'matchdict', None) is not None:
            self.__dict__.update(request.matchdict)

        self.__acl__ = []
        schedule = Schedule(request)

        if schedule.before_elections():
            self.__acl__.append((Allow, Everyone, 'browse'))

        elif schedule.during_elections():
            self.__acl__.append((Allow, Everyone, 'login'))
            self.__acl__.append((Allow, Authenticated, 'vote'))

        elif schedule.after_elections():
            self.__acl__.append((Allow, Everyone, 'results'))


class Candidate(Base):
    """Election candidate."""

    __tablename__ = 'candidates'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8',
        }

    #: Candidate number for a special "empty" candidate. The empty candidate has a
    #: valid candidate number which can be voted but does not count in the
    #: results for any of the real candidates.
    EMPTY_CANDIDATE = 0

    #: Primary key.
    id = Column(Integer, primary_key=True)
    #: Candidate number.
    number = Column(Integer, nullable=False, unique=True)
    #: First name of the candidate.
    firstname = Column(Unicode(255), nullable=False)
    #: Family name of the candidate.
    lastname = Column(Unicode(255), nullable=False)
    #: Slogan
    slogan = Column(Unicode(255), nullable=False)
    #: URL to personal page
    url = Column(Unicode(255), nullable=False)

    #: List of associated :py:class:`Vote` records.
    votes = relationship('Vote', backref='candidate', cascade='all')

    def __init__(self, number, firstname, lastname, slogan, url):
        """
        :param number: The candidate number.
        :type number: int

        :param firstname: The first name of the candidate.
        :type firstname: unicode

        :param lastname: The family name of the candidate.
        :type lastname: unicode

        :param slogan: Slogan for the candidate.
        :type slogan: unicode

        :param url: URL of an associated web site, such as a blog.
        :type url: unicode
        """
        self.number = number
        self.firstname = firstname.strip()
        self.lastname = lastname.strip()
        self.slogan = slogan.strip()
        self.url = url.strip()

    def is_empty(self):
        """Returns ``True`` if this candidate represents the special "empty"
        candidate, ``False`` otherwise.

        :rtype: bool
        """
        return self.number == Candidate.EMPTY_CANDIDATE

    def __repr__(self):
        """Detailed object representation."""
        return '<nuvavaalit.models.Candidate[name={0},number={1}] at {2}>'.format(
            self.fullname().encode('utf-8'), self.number, id(self))

    def fullname(self):
        """Returns the full name of the candidate.

        :rtype: unicode
        """
        if self.lastname.strip() and self.firstname.strip():
            return u'{0}, {1}'.format(self.lastname, self.firstname)

        return self.lastname.strip() or self.firstname.strip()


class Voter(Base):
    """Voter is an authenticated principal who is authorized to cast a vote."""

    __tablename__ = 'voters'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8',
        }

    #: Primary key.
    id = Column(Integer, primary_key=True)
    #: Username.
    username = Column(Unicode(255), unique=True, nullable=False)
    #: Encrypted password.
    _password = Column('password', String(255), nullable=False)
    #: First name(s).
    firstname = Column(Unicode(255), nullable=False)
    #: Last name.
    lastname = Column(Unicode(255), nullable=False)
    #: Opaque token to associate voters with additional datasets.
    token = Column(Unicode(255), nullable=True)

    def __init__(self, username, password, firstname, lastname, token=None):
        """
        :param username: Unique identifier for the user.
        :type username: unicode

        :param password: Password in plain-text. The password will be stored
                         in ``bcrypt`` encrypted form and will not be
                         available in plain-text form through this object.
        :type password: unicode

        :param firstname: First name(s)
        :type firstname: unicode

        :param lastname: Last name
        :type lastname: unicode
        """
        self.username = username
        self.password = password
        self.firstname = firstname
        self.lastname = lastname
        self.token = token

    def fullname(self):
        """Returns the full name of the voter.

        :rtype: unicode
        """
        return u'{0} {1}'.format(self.firstname, self.lastname)

    def has_voted(self):
        """Returns ``True`` if the voter has already voted in the election,
        ``False`` otherwise.

        :rtype: bool
        """
        session = DBSession()
        return session.query(func.COUNT(VotingLog.id)).filter(VotingLog.voter_id == self.id).scalar() > 0

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        """Stores the password in encrypted form."""
        self._password = password_manager.encodePassword(password)

    #: Encrypted password
    password = synonym('_password', descriptor=password)

    def check_password(self, password):
        """Returns ``True`` if the given ``password`` matches to stored one,
        ``False`` otherwise.

        :param password: The plain-text password to check.
        :type password: str

        :rtype: bool
        """
        return password_manager.checkPassword(self.password, password)


class Vote(Base):
    """Election vote."""

    __tablename__ = 'votes'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8',
        }

    #: Primary key.
    id = Column(Integer, primary_key=True)

    #: Foreign key reference to an associated :py:class:`Candidate` object.
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False, index=True)

    def __init__(self, candidate_or_id):
        """
        :param candidate_or_id: The :py:class:`Candidate` receiving the vote
        :type candidate_or_id: :py:class:`Candidate` or primary key
        """
        self.candidate_id = getattr(candidate_or_id, 'id', candidate_or_id)


class VotingLog(Base):
    """Record of a voter who has voted in the election.

    The primary use case is to keep track of voters who have already voted to
    prevent them from casting additional votes. The :py:attr:`voter_id`
    foreign key has a *UNIQUE* constraint which enforces the single vote per
    voter restriction on the database level.

    .. note:: The voting log specifically does not reference the
        actual :py:class:`Vote` which was cast.
    """

    __tablename__ = 'votinglog'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8',
        }

    #: Primary key.
    id = Column(Integer, primary_key=True)
    #: Timestamp when the vote was cast.
    timestamp = Column(Float, nullable=False)

    #: Foreign key to the :py:class:`Voter` instance who cast the vote.
    voter_id = Column(Integer, ForeignKey('voters.id'), nullable=False, unique=True)
    #: Reference to the associated :py:class:`Voter` instance.
    voter = relationship('Voter', uselist=False)

    def __init__(self, voter_or_id, timestamp=None):
        """
        :param voter_or_id: The :py:class:`Voter` who cast the vote
        :type voter_or_id: :py:class:`Voter` instance or primary key

        :param timestamp: The timestamp. If ``None``, defaults to ``time.time()``.
        :type timestamp: float
        """
        self.voter_id = getattr(voter_or_id, 'id', voter_or_id)
        self.timestamp = timestamp if timestamp is not None else time.time()


def initialize_sql(engine):
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
