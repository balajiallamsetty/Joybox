"""
Clean all collections in the configured database except the super admin account ('joybox_admin').
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from pymongo import MongoClient
from app.config import Config

def clean_database():
    uri = Config.MONGODB_URI
    db_name = Config.MONGODB_DB
    assert uri, "MONGODB_URI is required"
    assert db_name == "joybox_party_room", f"Expected joybox_party_room, got {db_name}"

    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    db = client[db_name]

    print(f"Target Database: {db_name}")
    print("--- BEFORE ---")
    for name in sorted(db.list_collection_names()):
        print(f"  {name}: {db[name].count_documents({})}")

    # In users collection, remove all users except 'joybox_admin'
    deleted_users = db["users"].delete_many({"username": {"$ne": "joybox_admin"}})
    print(f"Deleted other users from users collection: {deleted_users.deleted_count}")

    # In all other collections, delete all documents
    for name in sorted(db.list_collection_names()):
        if name == "users":
            continue
        del_res = db[name].delete_many({})
        print(f"Emptied {name}: removed {del_res.deleted_count}")

    print("--- AFTER ---")
    for name in sorted(db.list_collection_names()):
        print(f"  {name}: {db[name].count_documents({})}")

    # Verify super admin user exists
    superadmin = db["users"].find_one({"username": "joybox_admin"}, {"passwordHash": 0})
    print(f"Super Admin user present: {superadmin}")

if __name__ == "__main__":
    clean_database()

