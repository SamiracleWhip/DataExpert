import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

DB_PATH = os.environ.get("DB_PATH", "/tmp/rentals.db")

if Path(DB_PATH).exists():
    print(f"DB already present at {DB_PATH}, skipping download.")
    sys.exit(0)

required = ["R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"]
missing = [k for k in required if not os.environ.get(k)]
if missing:
    print(f"Missing env vars: {', '.join(missing)}", file=sys.stderr)
    sys.exit(1)

print(f"Downloading rentals.db from R2 to {DB_PATH}...")
s3 = boto3.client(
    "s3",
    endpoint_url=os.environ["R2_ENDPOINT_URL"],
    aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    region_name="auto",
)

try:
    s3.download_file(os.environ["R2_BUCKET"], "rentals.db", DB_PATH)
    print("Download complete.")
except ClientError as e:
    print(f"Download failed: {e}", file=sys.stderr)
    sys.exit(1)
