import os

API_KEY = os.environ.get("API_KEY", "")
API_BASE = os.environ.get("API_BASE", "https://api.deepseek.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-chat")

SLA_HOURS = 24
ANOMALY_STD_THRESHOLD = 2
ANOMALY_RING_THRESHOLD = 0.5
CLUSTER_WINDOW_HOURS = 24
CLUSTER_MIN_COUNT = 3

OUTPUT_DIR = "output"
REPORT_FILENAME = "analysis_report.md"
