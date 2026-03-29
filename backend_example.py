"""Backward-compatible launcher for the restructured backend."""

from backend.app import create_app


app = create_app()


if __name__ == '__main__':
    settings = app.config['SETTINGS']
    print('Starting backend server...')
    print(f"API address: http://localhost:{settings.app_port}")
    app.run(host=settings.app_host, port=settings.app_port, debug=settings.app_debug)


