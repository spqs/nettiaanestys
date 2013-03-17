from setuptools import find_packages
from setuptools import setup
import os

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()
version = '1.0b1'

requires = [
    'Babel',
    'BeautifulSoup',
    'MySQL-python',
    'Paste',
    'SQLAlchemy',
    'gunicorn',
    'isounidecode',
    'lingua',
    'mechanize',
    'mock',
    'openpyxl',
    'progressbar',
    'pycrypto',
    'pylibmc',
    'pyramid',
    'pyramid_beaker',
    'pyramid_debugtoolbar',
    'pyramid_exclog',
    'pyramid_tm',
    'repoze.filesafe',
    'setproctitle',
    'statsd-client',
    'transaction',
    'waitress',
    'webtest',
    'xlrd',
    'xlwt',
    'z3c.bcrypt',
    'zope.sqlalchemy',
    ]

setup(name='NuvaVaalit',
      version=version,
      description='NuvaVaalit',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pylons",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='Hexagon IT Oy',
      author_email='info@hexagonit.fi',
      url='http://www.hexagonit.fi',
      license='BSD',
      keywords='web wsgi pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='nuvavaalit',
      install_requires=requires,
      message_extractors = {
        '.': [
             ('**.py',   'lingua_python', None ),
             ('**.pt',   'lingua_xml', None ),
             ]},
      entry_points="""\
      [paste.app_factory]
      main = nuvavaalit:main

      [console_scripts]
      benchmark_crypto = nuvavaalit.scripts.benchmark_crypto:benchmark
      populate_candidates = nuvavaalit.scripts.populate:populate_candidates
      populate_test_users = nuvavaalit.scripts.populate:populate_test_users
      populate_voters = nuvavaalit.scripts.populate:populate_voters
      verify_voters = nuvavaalit.scripts.populate:verify_voters
      acceptance_test = nuvavaalit.scripts.acceptance:main
      """,
      paster_plugins=['pyramid'],
      )
