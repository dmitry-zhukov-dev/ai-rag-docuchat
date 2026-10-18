from app.integrations.qdrant import (
    COLLECTION_NAME,
    get_qdrant_client,
)


def main() -> None:
    client = get_qdrant_client()

    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=100,
        with_payload=True,
        with_vectors=False,
    )

    print(f"Points found: {len(points)}")

    for point in points:
        payload = point.payload or {}
        print(
            f"ID: {point.id}\n"
            f"Document ID: {payload.get('document_id')}\n"
            f"Chunk index: {payload.get('chunk_index')}\n"
            f"Text: {payload.get('text', '')[:100]}\n"
        )


if __name__ == "__main__":
    main()