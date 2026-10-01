from pathlib import Path

from datasets import load_dataset


OUTPUT_DIR = Path("data/benchmark/confluence")
TARGET_DOCUMENTS = 5_000


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(
        "onyx-dot-app/EnterpriseRAG-Bench",
        "documents",
        split="test",
        streaming=True,
    )

    extracted = 0

    for row in dataset:
        if row["source_type"] != "confluence":
            continue

        output_path = OUTPUT_DIR / f"{row['doc_id']}.txt"

        output_path.write_text(
            f"# {row['title']}\n\n{row['content']}",
            encoding="utf-8",
        )

        extracted += 1

        if extracted >= TARGET_DOCUMENTS:
            break

    print(f"Extracted: {extracted}")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()