#!/usr/bin/env python3
"""
Download building photos from PropertyGuru and generate CLIP image embeddings.

Reads building_photos rows where local_path IS NULL, downloads each image,
embeds it using CLIP (clip-ViT-B-32 via sentence-transformers), and upserts
into a 'building_images' ChromaDB collection.

Run from project root:
    python scripts/embed_photos.py [--limit N] [--batch-size N]

Resume-safe: skips photos that already have a local_path set.

Dependencies:
    pip install sentence-transformers Pillow requests
"""

import argparse
import sqlite3
import sys
import time
import uuid
from io import BytesIO
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "rentals.db"
CHROMA_PATH = PROJECT_ROOT / "backend" / "chroma_db"
PHOTO_CACHE = PROJECT_ROOT / "backend" / "photo_cache"

# Request headers for photo downloads
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36",
    "Referer": "https://www.propertyguru.com.sg/",
}

CLIP_MODEL = "clip-ViT-B-32"
COLLECTION_NAME = "building_images"


def _get_building_name(db: sqlite3.Connection, building_id: int) -> tuple[str, str]:
    row = db.execute(
        "SELECT project, street FROM buildings WHERE id = ?", [building_id]
    ).fetchone()
    return (row["project"], row["street"]) if row else ("Unknown", "")


def _get_district_area(db: sqlite3.Connection, building_id: int) -> tuple[str, str]:
    row = db.execute(
        """
        SELECT r.district, d.area_name
        FROM rental_contracts r
        JOIN districts d ON d.district = r.district
        WHERE r.building_id = ? LIMIT 1
        """,
        [building_id],
    ).fetchone()
    return (row["district"], row["area_name"]) if row else ("", "")


def download_photo(url: str, dest: Path) -> bool:
    """Download image URL to dest path. Returns True on success."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=20, stream=True)
        r.raise_for_status()
        content_type = r.headers.get("content-type", "")
        if "image" not in content_type and "jpeg" not in content_type and "png" not in content_type:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return dest.stat().st_size > 1000  # reject tiny/broken files
    except Exception:
        return False


def run(limit: int | None = None, batch_size: int = 32):
    if not DB_PATH.exists():
        print(f"Error: {DB_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    # Lazy imports — only needed at run time
    from PIL import Image
    import chromadb
    from sentence_transformers import SentenceTransformer

    print(f"Loading CLIP model '{CLIP_MODEL}'…")
    model = SentenceTransformer(CLIP_MODEL)

    print("Connecting to ChromaDB…")
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    # building_images collection stores raw embeddings (no embedding function —
    # we pass embeddings directly to avoid type mismatch with CLIP)
    collection = client.get_or_create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    # Fetch photos that need processing
    query = """
        SELECT p.id, p.building_id, p.pg_url, p.photo_order
        FROM building_photos p
        WHERE p.local_path IS NULL
        ORDER BY p.building_id, p.photo_order
    """
    if limit:
        query += f" LIMIT {limit}"
    rows = db.execute(query).fetchall()
    print(f"Photos to process: {len(rows)}")

    processed = 0
    failed = 0

    # Process in batches for efficient CLIP embedding
    batch: list[tuple] = []  # (row, pil_image, local_path)

    def flush_batch():
        nonlocal processed, failed
        if not batch:
            return

        images = [item[1] for item in batch]
        try:
            embeddings = model.encode(images, convert_to_numpy=True, show_progress_bar=False)
        except Exception as e:
            print(f"  CLIP encode error: {e}")
            failed += len(batch)
            batch.clear()
            return

        ids, docs, metas, embs = [], [], [], []
        for (row, _img, local_path), emb in zip(batch, embeddings):
            project, street = _get_building_name(db, row["building_id"])
            district, area = _get_district_area(db, row["building_id"])
            chroma_id = f"photo_{row['building_id']}_{row['photo_order']}"

            ids.append(chroma_id)
            docs.append(f"Photo of {project}, {street}. District {district} ({area}).")
            metas.append({
                "building_id": row["building_id"],
                "project": project,
                "district": district,
                "photo_order": row["photo_order"],
                "local_path": str(local_path),
            })
            embs.append(emb.tolist())

            # Update DB
            rel_path = str(local_path.relative_to(PROJECT_ROOT))
            db.execute(
                "UPDATE building_photos SET local_path = ?, chroma_id = ? WHERE id = ?",
                (rel_path, chroma_id, row["id"]),
            )
            processed += 1

        collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embs)
        db.commit()
        batch.clear()

    for i, row in enumerate(rows):
        bid = row["building_id"]
        order = row["photo_order"]
        dest = PHOTO_CACHE / str(bid) / f"{order}.jpg"

        print(f"[{i+1}/{len(rows)}] building={bid} photo={order}", end="  ")

        ok = download_photo(row["pg_url"], dest)
        if not ok:
            print("✗ download failed")
            failed += 1
            time.sleep(0.5)
            continue

        try:
            img = Image.open(dest).convert("RGB")
            # Resize to 224x224 for CLIP (model handles this but explicit is faster)
            img = img.resize((224, 224))
        except Exception as e:
            print(f"✗ image open failed: {e}")
            failed += 1
            continue

        batch.append((row, img, dest))
        print("✓ downloaded")
        time.sleep(0.3)  # Light rate limit for downloads

        if len(batch) >= batch_size:
            print(f"  → Embedding batch of {len(batch)}…")
            flush_batch()

    if batch:
        print(f"  → Embedding final batch of {len(batch)}…")
        flush_batch()

    db.close()

    total_in_collection = collection.count()
    print(f"\n✅ Done.")
    print(f"   Processed: {processed}")
    print(f"   Failed:    {failed}")
    print(f"   Collection '{COLLECTION_NAME}' now has {total_in_collection} embeddings.")
    print(f"   Photos cached at: {PHOTO_CACHE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download photos and generate CLIP embeddings")
    parser.add_argument("--limit", type=int, default=None, help="Max photos to process")
    parser.add_argument("--batch-size", type=int, default=32, help="CLIP batch size (default 32)")
    args = parser.parse_args()
    run(limit=args.limit, batch_size=args.batch_size)
