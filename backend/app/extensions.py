from pymongo import MongoClient
from pymongo.errors import PyMongoError

def init_mongo(app):
    uri = app.config.get("MONGODB_URI")
    db_name = app.config.get("MONGODB_DB", "joybox_party_room")
    if not uri or "<" in uri:
        app.extensions["mongo_client"] = None
        app.extensions["mongo_db"] = None
        app.logger.warning("MONGODB_URI missing or contains placeholder; database features will be inactive.")
        return

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=4000, tz_aware=True, appname="joybox-party-room")
        # Quick verification of server reachability
        client.admin.command("ping")
        app.extensions["mongo_client"] = client
        app.extensions["mongo_db"] = client[db_name]
        app.logger.info(f"Connected to MongoDB Atlas: {db_name}")
    except PyMongoError as exc:
        app.extensions["mongo_client"] = None
        app.extensions["mongo_db"] = None
        app.logger.warning(f"Failed to connect to MongoDB Atlas: {exc}")
