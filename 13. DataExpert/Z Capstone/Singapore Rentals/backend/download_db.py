import os
import sys
import zipfile
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

DB_PATH = os.environ.get("DB_PATH", "/tmp/rentals.db")
CHROMA_PATH = os.environ.get("CHROMA_PATH", "/tmp/chroma_db")

required = ["R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"]
missing = [k for k in required if not os.environ.get(k)]
if missing:
    print(f"Missing env vars: {', '.join(missing)}", file=sys.stderr)
    sys.exit(1)

s3 = boto3.client(
    "s3",
    endpoint_url=os.environ["R2_ENDPOINT_URL"],
    aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    region_name="auto",
)

def download(key, dest):
    print(f"Downloading {key} to {dest}...")
    try:
        s3.download_file(os.environ["R2_BUCKET"], key, dest)
        print(f"{key} download complete.")
    except ClientError as e:
        print(f"Download failed for {key}: {e}", file=sys.stderr)
        sys.exit(1)

if not Path(DB_PATH).exists():
    download("rentals.db", DB_PATH)
else:
    print(f"DB already present at {DB_PATH}, skipping.")

if not Path(CHROMA_PATH).exists():
    zip_path = "/tmp/chroma_db.zip"
    download("chroma_db.zip", zip_path)
    print("Extracting chroma_db...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall("/tmp")
    Path(zip_path).unlink()
    print("chroma_db ready.")
else:
    print(f"chroma_db already present at {CHROMA_PATH}, skipping.")
