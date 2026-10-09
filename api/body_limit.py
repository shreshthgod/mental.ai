"""Bound bytes before JSON parsing, including streamed/chunked requests."""
from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    def __init__(self, app, limit):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        root = scope.get('root_path', '')
        if root and path.startswith(root + '/'):
            path = path[len(root):]
        if scope['type'] != 'http' or path != '/predict' or scope['method'] != 'POST':
            return await self.app(scope, receive, send)
        limit = self.limit()
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            if len(body) + len(chunk) > limit:
                return await JSONResponse({'detail':'Request body exceeds service byte limit'},
                                          status_code=413)(scope, receive, send)
            body.extend(chunk)
            if not message.get('more_body', False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type':'http.request', 'body':bytes(body), 'more_body':False}
            return await receive()
        await self.app(scope, replay, send)
