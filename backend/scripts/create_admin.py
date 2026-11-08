import os
import sys
import argparse
import getpass
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.utils.db_safety import get_script_db_client, UnsafeDatabaseError

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    import werkzeug.security
    HAS_BCRYPT = False

load_dotenv()

import re

VALID_ROLES = ["owner", "manager", "staff"]

def validate_password_complexity(password: str) -> None:
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters long.")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one numeric digit.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValueError("Password must contain at least one special character.")

def hash_password(password: str) -> str:
    """Bcrypt password hasher with work factor 12 (or werkzeug scrypt fallback)."""
    if HAS_BCRYPT:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    else:
        return werkzeug.security.generate_password_hash(password, method="scrypt")

def create_admin_user(
    username: str,
    email: str,
    display_name: str,
    password: str,
    role: str,
    db_name: str = None,
    uri: str = None,
    allow_production: bool = False,
    confirm_token: str = None,
    db = None
):
    if db is None:
        if not db_name:
            print("[!] ERROR: Explicit --db target is required.")
            sys.exit(1)
        try:
            client, db = get_script_db_client(
                db_name=db_name,
                uri=uri,
                allow_production=allow_production,
                confirm_token=confirm_token,
                appname="joybox-create-admin"
            )
        except UnsafeDatabaseError as e:
            print(f"[!] SAFETY ERROR: {e}")
            sys.exit(1)

    db_target = db.name
    role_clean = role.strip().lower()
    if role_clean not in VALID_ROLES:
        print(f"[!] Invalid role '{role}'. Must be one of {VALID_ROLES}")
        sys.exit(1)

    try:
        validate_password_complexity(password)
    except ValueError as ve:
        print(f"[!] PASSWORD POLICY VIOLATION: {ve}")
        sys.exit(1)

    now = datetime.now(timezone.utc)

    admin_doc = {
        "username": username.strip().lower(),
        "email": email.strip().lower(),
        "displayName": display_name.strip(),
        "passwordHash": hash_password(password),
        "role": role_clean,
        "isActive": True,
        "failedLoginAttempts": 0,
        "lockoutUntil": None,
        "schemaVersion": 1,
        "updatedAt": now
    }

    res = db.users.update_one(
        {"username": admin_doc["username"]},
        {"$set": admin_doc, "$setOnInsert": {"createdAt": now}},
        upsert=True
    )
    action = "Created" if res.upserted_id else "Updated"
    print(f"[+] Successfully {action} {role_clean} user '{admin_doc['username']}' in database '{db_target}'.")

def main():
    parser = argparse.ArgumentParser(description="Create or update a Joybox admin user.")
    parser.add_argument("--username", help="Admin username")
    parser.add_argument("--email", help="Admin email")
    parser.add_argument("--display-name", help="Display name")
    parser.add_argument("--password", help="Password (plain text or prompt)")
    parser.add_argument("--role", default="owner", choices=VALID_ROLES, help="Role: owner, manager, staff")
    parser.add_argument("--db", required=True, help="Target database name (e.g. joybox_party_room_test)")
    parser.add_argument("--allow-production", action="store_true", help="Explicit flag required to target production database")
    parser.add_argument("--confirm-production", default=None, help="Must match database name if targeting production")

    args = parser.parse_args()

    if args.username and args.password:
        create_admin_user(
            username=args.username,
            email=args.email or f"{args.username}@joyboxparty.in",
            display_name=args.display_name or args.username.title(),
            password=args.password,
            role=args.role,
            db_name=args.db,
            allow_production=args.allow_production,
            confirm_token=args.confirm_production
        )
        return

    print("--- Joybox Party Room: Create Admin User ---")
    username = input("Username: ").strip().lower()
    email = input("Email: ").strip().lower()
    display_name = input("Display Name: ").strip()
    role = input("Role (owner, manager, staff): ").strip().lower()
    if not username or not email or not display_name or not role:
        print("[!] Username, email, display name, and role are required. No defaults are applied.")
        sys.exit(1)

    password = getpass.getpass("Password: ").strip()
    if not password:
        print("[!] Password cannot be empty.")
        sys.exit(1)

    confirm = getpass.getpass("Confirm Password: ").strip()
    if password != confirm:
        print("[!] Passwords do not match.")
        sys.exit(1)

    create_admin_user(
        username=username,
        email=email,
        display_name=display_name,
        password=password,
        role=role,
        db_name=args.db,
        allow_production=args.allow_production,
        confirm_token=args.confirm_production
    )

if __name__ == "__main__":
    main()
