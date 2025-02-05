import hashlib


def md5(text) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()