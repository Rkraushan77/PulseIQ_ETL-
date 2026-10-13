
from pathlib import Path


def save_data(df, folder, file_name):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)

    file_path = folder / file_name
    df.to_csv(file_path, index=False)

    print(f"Saved {len(df)} rows to {file_path}")
