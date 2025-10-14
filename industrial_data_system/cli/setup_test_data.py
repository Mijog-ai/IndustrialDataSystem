"""Populate the database and shared drive with sample data for testing."""

from __future__ import annotations

from industrial_data_system.pipelines import create_sample_dataset


def main() -> None:
    print("Setting up sample test data...")
    result = create_sample_dataset()

    if result["user_created"]:
        print("Created sample user: sample_uploader@example.com")
    else:
        print("Using existing sample user: sample_uploader@example.com")

    for path in result["files"]:
        print(f"Created sample upload: {path}")

    print(
        "Sample data setup complete. "
        f"{result['uploads_created']} uploads available for exploration."
    )


if __name__ == "__main__":
    main()
