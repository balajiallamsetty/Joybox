import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

# Ensure safe DB name
load_dotenv("backend/.env")
load_dotenv()

uri = os.getenv("MONGODB_TEST_URI") or os.getenv("MONGODB_URI", "")
test_db_name = os.getenv("MONGODB_TEST_DB", "joybox_party_room_test")

if not test_db_name.endswith("_test"):
    print(f"ABORTED: {test_db_name} does not end in _test")
    sys.exit(1)

client = MongoClient(uri, serverSelectionTimeoutMS=5000, tz_aware=True)
db = client[test_db_name]

print(f"Target test database: {db.name}")

# Print slotClaims indexes
print("\n--- slotClaims Index Information ---")
for idx_name, idx_info in db.slotClaims.index_information().items():
    print(f"Index '{idx_name}': {idx_info}")

# Print a sample claim
print("\n--- Sample slotClaims Document ---")
sample = db.slotClaims.find_one()
if sample:
    # Redact sensitive IDs if any
    print({k: (str(v) if k in ["_id", "ownerId"] else v) for k, v in sample.items()})
else:
    print("No slotClaims documents found in test database.")

# Count documents
print(f"\nTotal slotClaims count in test db: {db.slotClaims.count_documents({})}")

