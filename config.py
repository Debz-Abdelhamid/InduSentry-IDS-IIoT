from __future__ import annotations

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.environ.get("SECRET_KEY", "ids-iiot-dev-secret")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
MODEL_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

ALLOWED_EXTENSIONS = {".csv"}
MAX_CONTENT_LENGTH = 1024 * 1024 * 1024

SOCKETIO_ASYNC_MODE = os.environ.get("SOCKETIO_ASYNC_MODE", "eventlet")

PROCESSING_CHUNK_SIZE = int(os.environ.get("PROCESSING_CHUNK_SIZE", "512"))
AE_BATCH_SIZE = int(os.environ.get("AE_BATCH_SIZE", "4096"))
AE_EMIT_EVERY = int(os.environ.get("AE_EMIT_EVERY", "5000"))
XGB_EMIT_EVERY = int(os.environ.get("XGB_EMIT_EVERY", "5000"))

OOD_TRAIN_SAMPLES = int(os.environ.get("OOD_TRAIN_SAMPLES", "5000"))
OOD_NORMAL_SAMPLE_SIZE = int(os.environ.get("OOD_NORMAL_SAMPLE_SIZE", "5000"))
OOD_THRESHOLD_FALLBACK = float(os.environ.get("OOD_THRESHOLD_FALLBACK", "0.60"))

ZERO_DAY_POST_CORRECTION = os.environ.get("ZERO_DAY_POST_CORRECTION", "off").lower()
LABELS_FILENAME = os.environ.get("LABELS_FILENAME", "y_test_hybrid_type.csv")
LABELS_COLUMN = os.environ.get("LABELS_COLUMN", "Attack_type")

LATENCY_MS_DEFAULT = int(os.environ.get("LATENCY_MS_DEFAULT", "14"))
SECURITY_LEVEL_DEFAULT = os.environ.get("SECURITY_LEVEL_DEFAULT", "MAXIMUM")
