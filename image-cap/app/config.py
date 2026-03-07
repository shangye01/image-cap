# config.py
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# 强制加载项目根目录的 .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
print(f"DEBUG: env_path = {env_path}")
print(f"DEBUG: SUPABASE_URL = {SUPABASE_URL[:30]}..." if SUPABASE_URL else "None")
print(f"DEBUG: SUPABASE_SERVICE_KEY exists = {bool(SUPABASE_SERVICE_KEY)}")

# 先定义默认值，防止导入失败
supabase = None

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("WARNING: 缺少 Supabase 配置，使用空客户端")
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("DEBUG: Supabase 客户端创建成功")
    except Exception as e:
        print(f"ERROR: 创建 Supabase 客户端失败: {e}")
        import traceback
        traceback.print_exc()
        # 不抛出异常，让导入继续
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
    }
}