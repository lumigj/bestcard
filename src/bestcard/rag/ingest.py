from pathlib import Path


def main() -> None:
    raw_dir = Path("data/rag/raw")
    chunk_dir = Path("data/rag/chunks")
    chunk_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(raw_dir.glob("*"))
    if not files:
        print("No raw policy docs found in data/rag/raw")
        return

    # Placeholder: real implementation should split docs and push embeddings.
    for file in files:
        out = chunk_dir / f"{file.stem}.chunk.txt"
        out.write_text(file.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Ingested {len(files)} document(s) into {chunk_dir}")


if __name__ == "__main__":
    main()
