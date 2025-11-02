import random, string

def random_code(n=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))