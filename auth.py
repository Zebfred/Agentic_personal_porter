from werkzeug.security import generate_password_hash, check_password_hash

def hash_password(password):
    """Hashes a password using PBKDF2 with a salt."""
    return generate_password_hash(password)

def check_password(hashed_password, password):
    """Verifies a password against a hash."""
    return check_password_hash(hashed_password, password)