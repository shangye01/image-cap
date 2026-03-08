# config.py
import os

from pathlib import Path
from dotenv import load_dotenv
from supabase import Client, create_client

# 强制加载项目根目录的 .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client | None = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except Exception:
        # 保持为 None，由认证接口返回清晰错误
        supabase = None

# 训练配置
TRAINING_CONFIG = {
    "augmentation": {
        "degrees": 15.0,
        "translate": 0.2,
        "scale": 0.5,
        "shear": 5.0,
        "flipud": 0.3,
        "fliplr": 0.5,
        "hsv_h": 0.015,
        "hsv_s": 0.7,
        "hsv_v": 0.4,
        "mosaic": 1.0,
        "mixup": 0.1,
    },
    "optimizer": {
        "type": "AdamW",
        "lr0": 0.001,
        "lrf": 0.01,
        "momentum": 0.937,
        "weight_decay": 0.0005,
        "warmup_epochs": 3,
    },
    "training": {
        "epochs": 100,
        "patience": 20,
        "batch": 16,
        "imgsz": 640,
        "amp": True,
    },
}