# core/config.py
# import os
# from dotenv import load_dotenv

# load_dotenv()

# GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# if not GOOGLE_MAPS_API_KEY:
#     raise RuntimeError("GOOGLE_MAPS_API_KEY not set")

import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not GOOGLE_MAPS_API_KEY:
    raise RuntimeError("GOOGLE_MAPS_API_KEY not set")

