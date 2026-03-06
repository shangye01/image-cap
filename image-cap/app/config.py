import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("缺少Supabase配置，请检查.env文件")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

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
    }
}