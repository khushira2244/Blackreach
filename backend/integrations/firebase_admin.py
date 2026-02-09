import os
from typing import Any, Dict, Optional

import firebase_admin
from firebase_admin import credentials, db

_initialized = False



def init_firebase() -> None:
    """
    Initialize Firebase Admin SDK once.
    Requires env vars:
      - FIREBASE_SERVICE_ACCOUNT_PATH
      - FIREBASE_DATABASE_URL
    """
    global _initialized
    if _initialized:
        return

    sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    db_url = os.getenv("FIREBASE_DATABASE_URL")
  

    if not sa_path:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_PATH missing in environment")
    if not db_url:
        raise RuntimeError("FIREBASE_DATABASE_URL missing in environment")

    cred = credentials.Certificate(sa_path)
    firebase_admin.initialize_app(cred, {"databaseURL": db_url})
    _initialized = True


def rtdb_set(path: str, value: Dict[str, Any]) -> None:
    """
    Set data at a fixed path.
    Example: /live/{bookingId}/latest
    """
    init_firebase()
    db.reference(path).set(value)


def rtdb_push(path: str, value: Dict[str, Any]) -> Optional[str]:
    """
    Push data under a path (creates auto-id).
    Example: /live/{bookingId}/history
    """
    init_firebase()
    ref = db.reference(path).push(value)
    return ref.key
