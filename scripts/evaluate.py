from pathlib import Path


def main() -> None:
    output_dir = Path(__file__).resolve().parents[1] / 'outputs' / 'reports'
    output_dir.mkdir(parents=True, exist_ok=True)
    print('Evaluation scaffold is ready.')
    print(f'Report outputs: {output_dir}')


if __name__ == '__main__':
    main()
