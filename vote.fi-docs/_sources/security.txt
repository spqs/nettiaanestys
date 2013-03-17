Security
========

Data storage
------------

**Passwords**

    Passwords are stored as salted hashes using the `bcrypt
    <http://en.wikipedia.org/wiki/Bcrypt>`_ hashing scheme. The ``bcrypt``
    hashing scheme is particularly suitable for storing hashed passwords as it
    makes brute force attacks more difficult, see

        * http://codahale.com/how-to-safely-store-a-password
        * http://chargen.matasano.com/chargen/2007/9/7/enough-with-the-rainbow-tables-what-you-need-to-know-about-s.html

**Votes**

    The votes are stored separately from the voter information so that the
    data model does not allow the votes to be associated with the voters
    after casting the vote.

**Session data**

    Session data is stored in a volatile in-memory storage (memcached) which
    is not explicitly written to disk. Access to the session storage is
    restricted.

**Logging**

    The logging data produced by the system is meant for auditing purposes and
    does not compromise the confidentiality of the election nor reveal cast
    votes.


OWASP 10 analysis
-----------------

The `Open Web Application Security Project <http://www.owasp.org/>`_ (OWASP)
is a 501c3 not-for-profit worldwide charitable organization focused on
improving the security of application software.

The OWASP Top Ten represents a broad consensus about what the most critical
web application security flaws are. Below are listed the top ten security
flaws for 2010 commented in the context of the application. The full `OWASP
Top 10 for 2010
<http://owasptop10.googlecode.com/files/OWASP%20Top%2010%20-%202010.pdf>`_
document is downloadable in PDF form.

A1 - Injection
''''''''''''''

  *“Injection flaws, such as SQL, OS, and LDAP injection, occur when untrusted
  data is sent to an interpreter as part of a command or query. The attacker’s
  hostile data can trick the interpreter into executing unintended commands or
  accessing unauthorized data.”*

All SQL commands are mediated by the `SQLAlchemy <http://sqlalchemy.org/>`_
`ORM <http://www.sqlalchemy.org/docs/orm/index.html>`_ which uses bind
parameters to automatically quote all parameterized queries which greatly
reduces the risk of a successful SQL injection attack. The application does
not manipulate any SQL queries as text.

The only attack vector for injecting data which is directly related to a
database write operation is casting of the vote. The value of the vote is an
integer corresponding to a candidate election number. The value is validated
before storing. (See :py:func:`nuvavaalit.views.voting.vote` for
implementation details.)

A2 - Cross-Site Scripting (XSS)
'''''''''''''''''''''''''''''''

  *“XSS flaws occur whenever an application takes untrusted data and sends it
  to a web browser without proper validation and escaping. XSS allows
  attackers to execute scripts in the victim’s browser which can hijack user
  sessions, deface web sites, or redirect the user to malicious sites.”*

The application does not accept input for rendering from the user.

A3 - Broken Authentication and Session Management
'''''''''''''''''''''''''''''''''''''''''''''''''

  *“Application functions related to authentication and session management are
  often not implemented correctly, allowing attackers to compromise passwords,
  keys, session tokens, or exploit other implementation flaws to assume other
  users’ identities.”*

The authenticated state is maintained using a cookie-based `auth_tkt
<http://www.openfusion.com.au/labs/mod_auth_tkt/>`_ session scheme. The
authentication ticket is valid for 20 minutes and gets reissued every 2
minutes. The ticket is valid for a single originating ip-address and the
cookie is served using the **secure** (TLS connections only) and **httponly**
(not visible to Javascript) modes.

The session identifier (auth ticket) is not exposed in the URL space of the
application at any time. Additionally, the session identifier can not be set
directly in a GET / POST request reducing the risk of `session fixation
<http://en.wikipedia.org/wiki/Session_fixation>`_ attacks.

The user will automatically be logged out and the auth ticket invalidated when
the voting process is successfully completed. Regardless of logout the
authentication ticket is only valid for a single browser session.

The application operates exclusively over a TLS connection.

A4 - Insecure Direct Object References
''''''''''''''''''''''''''''''''''''''

  *“A direct object reference occurs when a developer exposes a reference to
  an internal implementation object, such as a file, directory, or database
  key. Without an access control check or other protection, attackers can
  manipulate these references to access unauthorized data.”*

The application does not expose any direct object references. Additionally,
all object references are validated at the time of use.

A5 - Cross-Site Forgery (CSRF)
''''''''''''''''''''''''''''''

  *“A CSRF attack forces a logged-on victim’s browser to send a forged HTTP
  request, including the victim’s session cookie and any other automatically
  included authentication information, to a vulnerable web application. This
  allows the attacker to force the victim’s browser to generate requests the
  vulnerable application thinks are legitimate requests from the victim.”*

All of the application forms are protected with session specific CSRF tokens
which are validated when processing the form submissions. The forms also
explicitly require the POST method to further reduce the risk of passive
CSRF attacks using GET method request.

A6 - Security Misconfiguration
''''''''''''''''''''''''''''''

  *“Good security requires having a secure configuration defined and deployed
  for the application, frameworks, application server, web server, database
  server, and platform. All these settings should be defined, implemented, and
  maintained as many are not shipped with secure defaults. This includes
  keeping all software up to date, including all code libraries used by the
  application.”*

A7 - Insecure Cryptographic Storage
'''''''''''''''''''''''''''''''''''

  *“Many web applications do not properly protect sensitive data, such as
  credit cards, SSNs, and authentication credentials, with appropriate
  encryption or hashing. Attackers may steal or modify such weakly protected
  data to conduct identity theft, credit card fraud, or other crimes.”*

The only sensitive user information is the password which is stored in a
salted hashed form using the `bcrypt <http://en.wikipedia.org/wiki/Bcrypt>`_
hashing scheme. The ``bcrypt`` hashing scheme is particularly suitable for
storing hashed passwords, see

    * http://codahale.com/how-to-safely-store-a-password
    * http://chargen.matasano.com/chargen/2007/9/7/enough-with-the-rainbow-tables-what-you-need-to-know-about-s.html

A8 - Failure to Restrict URL Access
'''''''''''''''''''''''''''''''''''

  *“Many web applications check URL access rights before rendering protected
  links and buttons. However, applications need to perform similar access
  control checks each time these pages are accessed, or attackers will be able
  to forge URLs to access these hidden pages anyway.”*

Each URL access in the application is verified separately.

A9 - Insufficient Transport Layer Protection
''''''''''''''''''''''''''''''''''''''''''''

  *“Applications frequently fail to authenticate, encrypt, and protect the
  confidentiality and integrity of sensitive network traffic. When they do,
  they sometimes support weak algorithms, use expired or invalid certificates,
  or do not use them correctly.”*

The application is made available only over a TLS connection and all cookies
are served with the **secure** flag enabled.

A10 - Unvalidated Redirects and Forwards
''''''''''''''''''''''''''''''''''''''''

  *“Web applications frequently redirect and forward users to other pages and
  websites, and use untrusted data to determine the destination pages. Without
  proper validation, attackers can redirect victims to phishing or malware
  sites, or use forwards to access unauthorized pages.”*

All redirects produced by the system are generated using the framework tools
and none are parameterized.
