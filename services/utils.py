import random, string

def random_code(n=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))