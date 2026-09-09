"""
Central config loader.
Every other module should import from here instead of reading
config.ini / .env directly. This keeps all config access in one place,
so if you ever change how config is stored, you only edit this file.
"""

import configparser
import os
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Project root = parent of src/
ROOT_DIR = Path(__file__).resolve().parent.parent

# Load secrets from .env (DB host/user/password)
load_dotenv(ROOT_DIR / ".env")

# Load non-secret params from config.ini
_config = configparser.ConfigParser()
_config.read(ROOT_DIR / "config.ini")

# ---- Paths ----
RAW_DATA_DIR = ROOT_DIR / _config.get("paths", "raw_data_dir")
INTERIM_DATA_DIR = ROOT_DIR / _config.get("paths", "interim_data_dir")
PROCESSED_DATA_DIR = ROOT_DIR / _config.get("paths", "processed_data_dir")
MODELS_DIR = ROOT_DIR / _config.get("paths", "models_dir")
LOGS_DIR = ROOT_DIR / _config.get("paths", "logs_dir")

for _dir in (RAW_DATA_DIR, INTERIM_DATA_DIR, PROCESSED_DATA_DIR, MODELS_DIR, LOGS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ---- Database (secrets from .env / environment) ----
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "retail_customer_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

_DATABASE_URL = os.getenv("DATABASE_URL")
if _DATABASE_URL:
    DATABASE_URL = _DATABASE_URL
else:
    _password_part = f":{quote_plus(POSTGRES_PASSWORD)}" if POSTGRES_PASSWORD else ""
    DATABASE_URL = (
        f"postgresql+psycopg2://{quote_plus(POSTGRES_USER)}{_password_part}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

# ---- Pipeline params ----
REFERENCE_DATE = _config.get("pipeline", "reference_date")  # "auto" or "YYYY-MM-DD"

# ---- Segmentation params ----
N_CLUSTERS = _config.getint("segmentation", "n_clusters")
RANDOM_STATE = _config.getint("segmentation", "random_state")
KMEANS_N_INIT = _config.getint("segmentation", "kmeans_n_init")

# ---- Order filter ----
VALID_ORDER_STATUS = _config.get("order_filter", "valid_status")
