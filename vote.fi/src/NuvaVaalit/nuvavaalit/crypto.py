from Crypto.Cipher import AES
from cStringIO import StringIO
import binascii
import hashlib
import random
import time
import uuid


def session_key():
    """Generates a random key that can be used as an encryption key during a
    user session.

    :rtype: str
    """
    key = hashlib.sha512()
    key.update(str(uuid.uuid4()))
    key.update(repr(time.time()))
    return key.hexdigest()


def generate_iv():
    """Generates a random IV (initial vector) value.

    The IV consists of 16 random bytes.

    :rtype: str
    """
    return ''.join(chr(random.randint(0, 0xFF)) for i in xrange(16))


def encrypt(data, key):
    """Encrypts the given data using AES in cipher feedback mode (CFB) with
    the given password.

    :param key: Encryption password.
    :type key: str

    :param data: Data to encrypt.
    :type data: str

    :return: A hexadecimal string representation of the encrypted data
    :rtype: str
    """
    chunks = lambda l, n: [l[x: x + n] for x in xrange(0, len(l), n)]
    secret = hashlib.md5(key).hexdigest()
    iv = generate_iv()
    encryptor = AES.new(secret, AES.MODE_CFB, iv)

    outfile = StringIO()
    outfile.write(iv)
    for c in chunks(str(data), 16):
        outfile.write(encryptor.encrypt(c))

    return binascii.hexlify(outfile.getvalue())


def decrypt(data, key):
    """Decrypts the given data.

    The data must have been encrypted using AES in cipher feeback (CFB) mode
    and serialized in a hexadecimal string representation.

    .. note:: There is no way for this function to detect whether the given
              key is correct or not. Using an invalid key will
              result in the data to decrypt as nonsense. It is up to the
              caller to determine whether decryption was successful or not.

    :param data: The encrypted data in hexadecimal string form.
    :type data: str

    :param key: The decryption password.
    :type key: str

    :rtype: str
    """
    secret = hashlib.md5(key).hexdigest()
    infile = StringIO(binascii.unhexlify(data))

    iv = infile.read(16)
    decryptor = AES.new(secret, AES.MODE_CFB, iv)
    data = []
    while True:
        chunk = infile.read(16)
        if len(chunk) == 0:
            break
        data.append(decryptor.decrypt(chunk))

    return ''.join(data)
