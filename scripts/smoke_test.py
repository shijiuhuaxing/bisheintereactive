import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from backend.app import create_app


def main() -> None:
    app = create_app()
    client = app.test_client()

    response = client.get('/api/health')
    print('Health endpoint status:', response.status_code)
    print('Health payload:', response.get_json())


if __name__ == '__main__':
    main()
