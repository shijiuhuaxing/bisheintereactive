from __future__ import annotations

import http.server
import mimetypes
import socketserver
from pathlib import Path


PORT = 8000
FRONTEND_DIR = Path(__file__).resolve().parents[1] / 'frontend'


def main() -> None:
    mimetypes.add_type('text/javascript; charset=utf-8', '.js')
    mimetypes.add_type('text/javascript; charset=utf-8', '.mjs')
    mimetypes.add_type('model/gltf-binary', '.glb')
    mimetypes.add_type('application/wasm', '.wasm')

    handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *args,
        directory=str(FRONTEND_DIR),
        **kwargs,
    )
    with socketserver.TCPServer(('', PORT), handler) as httpd:
        print(f'Frontend server: http://127.0.0.1:{PORT}')
        print(f'Root: {FRONTEND_DIR}')
        httpd.serve_forever()


if __name__ == '__main__':
    main()
