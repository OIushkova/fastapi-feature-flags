import secrets


def generate_new_key():
    return secrets.token_urlsafe(16)
