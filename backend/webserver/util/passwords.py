"""Password hashing that stays compatible with databases created by the
original coco-annotator (werkzeug < 2.3, ``method='sha256'``).

Werkzeug 3 can no longer verify the old ``sha256$salt$hex`` hashes, so they
are checked here directly and upgraded to the current default on login.
"""
import hashlib
import hmac

from werkzeug.security import (
    check_password_hash as _werkzeug_check,
    generate_password_hash,
)

_LEGACY_METHODS = {"sha1", "sha224", "sha256", "sha384", "sha512", "md5"}


def hash_password(password):
    return generate_password_hash(password)


def is_legacy_hash(pwhash):
    return bool(pwhash) and pwhash.split("$", 1)[0] in _LEGACY_METHODS


def check_password(pwhash, password):
    if not pwhash or password is None:
        return False

    if is_legacy_hash(pwhash):
        try:
            method, salt, digest = pwhash.split("$", 2)
        except ValueError:
            return False
        if salt:
            actual = hmac.new(salt.encode(), password.encode(), method).hexdigest()
        else:
            actual = hashlib.new(method, password.encode()).hexdigest()
        return hmac.compare_digest(actual, digest)

    return _werkzeug_check(pwhash, password)


def check_and_upgrade(user, password):
    """Verify ``password`` for ``user``; rehash legacy hashes on success."""
    if not check_password(user.password, password):
        return False
    if is_legacy_hash(user.password):
        new_hash = hash_password(password)
        user.update(password=new_hash)
        user.password = new_hash
    return True
