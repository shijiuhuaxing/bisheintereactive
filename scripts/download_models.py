from pathlib import Path


def main() -> None:
    checkpoint_dir = Path(__file__).resolve().parents[1] / 'models' / 'checkpoints'
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    print(f'Model checkpoints directory is ready: {checkpoint_dir}')
    print('Add actual model download logic in later iterations.')


if __name__ == '__main__':
    main()
