# -*- coding: utf-8 -*-
import unittest


class TestCrypto(unittest.TestCase):
    """Docstring."""

    maxDiff = None

    def test_session_key(self):
        """Generate a bunch of session keys to make sure we don't generate duplicates."""
        from nuvavaalit.crypto import session_key
        keys = set()
        for i in xrange(1000):
            key = session_key()
            self.assertFalse(key in keys, 'session_key() generated a duplicate value')
            keys.add(key)
        self.assertEquals(1000, len(keys))

    def test_encryption_roundtrip(self):
        """Ensure that we can pass information through an encrypt/decrypt cycle."""
        from nuvavaalit.crypto import encrypt
        from nuvavaalit.crypto import decrypt

        for value in '1', 'foo', 'fööbär':
            self.assertEquals(value, decrypt(encrypt(value, 'secret'), 'secret'))

    def test_encrypt(self):
        """Ensure that encryption does mangles the data."""
        from nuvavaalit.crypto import encrypt

        self.assertFalse('value' in encrypt('value', 'secret'))
