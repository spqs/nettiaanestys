import timeit


def benchmark():
    statement = """assert 'my secret' == decrypt(encrypt('my secret', 'secret key'), 'secret key')"""

    setup = """from nuvavaalit.crypto import encrypt, decrypt"""

    vectors = timeit.repeat(statement, setup, repeat=3, number=100000)
    print 'encrypt/decrypt cycle: minimum {:.2f} usec/pass with {} iterations'.format(1000000 * min(vectors) / 100000, 3 * 100000)
