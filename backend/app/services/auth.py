"""Auth0 JWT authentication — stub.

Provides a ``requires_auth`` decorator that will validate JWTs
once Auth0 domain / audience are configured.
"""

from functools import wraps
from flask import jsonify


def requires_auth(f):
    """Decorator that protects a Flask route with Auth0 JWT validation.

    Currently a pass-through stub.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        # TODO: implement real JWT validation with python-jose
        # For now, pass through so routes are callable in development
        return f(*args, **kwargs)

    return decorated
