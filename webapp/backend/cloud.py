"""Authenticated cloud entry point; the local replay app stays unchanged."""
import base64
import binascii
import os
import secrets
from fastapi import FastAPI
from starlette.responses import JSONResponse
from webapp.backend.replay import app as replay_app, bundle
from webapp.backend.model_inference import artifacts


class DemoLogin:
    def __init__(self, app, username, password):
        self.app, self.username, self.password = app, username, password

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope.get('path') == '/healthz':
            return await self.app(scope, receive, send)
        header = dict(scope['headers']).get(b'authorization', b'')
        valid = False
        try:
            scheme, token = header.split(b' ', 1)
            if scheme.lower() == b'basic':
                user, password = base64.b64decode(token, validate=True).split(b':', 1)
                valid = (secrets.compare_digest(user, self.username.encode()) &
                         secrets.compare_digest(password, self.password.encode()))
        except (ValueError, binascii.Error):
            pass
        if not valid:
            response = JSONResponse({'detail': 'Demo login required.'}, status_code=401,
                headers={'WWW-Authenticate': 'Basic realm="HOMIE demo", charset="UTF-8"',
                         'Cache-Control': 'no-store'})
            return await response(scope, receive, send)
        return await self.app(scope, receive, send)


def create_app():
    username = os.environ.get('HOMIE_DEMO_USER', '')
    password = os.environ.get('HOMIE_DEMO_PASSWORD', '')
    if not username or ':' in username or len(password) < 16:
        raise RuntimeError('Set HOMIE_DEMO_USER (without a colon) and HOMIE_DEMO_PASSWORD (at least 16 characters).')
    # Fail startup if the deployment omitted artifacts, instead of showing a broken demo.
    artifacts()
    bundle()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get('/healthz')
    def health():
        return {'status': 'ok'}

    app.add_middleware(DemoLogin, username=username, password=password)
    app.mount('/', replay_app)
    return app
