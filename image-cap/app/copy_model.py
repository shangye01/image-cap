#!/usr/bin/env python3
"""
自动复制训练好的模型到 models 目录
并修复数据库记录
"""

import shutil
import json
from pathlib import Path
from datetime import datetime
import sys


def find_latest_model():
    """找到最新的训练模型"""
    runs_dir = Path("runs/train")

    if not runs_dir.exists():
        print("❌ 错误: runs/train 目录不存在")
        print("   请先完成训练")
        return None

    # 找最新的训练目录
    train_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
    if not train_dirs:
        print("❌ 错误: 没有找到训练目录")
        return None

    # 按修改时间排序
    latest_dir = max(train_dirs, key=lambda x: x.stat().st_mtime)

    # 检查模型文件
    weights_dir = latest_dir / "weights"
    best_pt = weights_dir / "best.pt"

    if not best_pt.exists():
        print(f"❌ 错误: 未找到模型文件 {best_pt}")
        return None

    return {
        "train_dir": latest_dir,
        "best_pt": best_pt,
        "last_pt": weights_dir / "last.pt",
        "results": latest_dir / "results.csv"
    }


def parse_results(results_file):
    """解析训练结果"""
    if not results_file.exists():
        return {}

    lines = results_file.read_text().strip().split('\n')
    if len(lines) < 2:
        return {}

    # 读取最后一行（最佳结果）
    # 格式: epoch, box_loss, cls_loss, dfl_loss, precision, recall, mAP50, mAP75, mAP50-95
    headers = lines[0].split(',')
    last_line = lines[-1].split(',')

    try:
        return {
            "epochs": len(lines) - 1,
            "box_loss": float(last_line[1]) if len(last_line) > 1 else 0,
            "cls_loss": float(last_line[2]) if len(last_line) > 2 else 0,
            "precision": float(last_line[4]) if len(last_line) > 4 else 0,
            "recall": float(last_line[5]) if len(last_line) > 5 else 0,
            "mAP50": float(last_line[6]) if len(last_line) > 6 else 0,
            "mAP75": float(last_line[7]) if len(last_line) > 7 else 0,
            "mAP50_95": float(last_line[8]) if len(last_line) > 8 else 0,
        }
    except Exception as e:
        print(f"⚠️ 解析结果文件失败: {e}")
        return {}


def copy_model():
    """复制模型到 models 目录"""

    print("=" * 60)
    print("🚀 模型复制工具")
    print("=" * 60)

    # 1. 找到最新模型
    print("\n1. 查找最新训练模型...")
    model_info = find_latest_model()
    if not model_info:
        return False

    train_dir = model_info["train_dir"]
    best_pt = model_info["best_pt"]

    print(f"   ✅ 找到: {train_dir.name}")
    print(f"   📁 路径: {train_dir}")
    print(f"   📊 大小: {best_pt.stat().st_size / (1024 * 1024):.1f} MB")

    # 2. 解析训练结果
    print("\n2. 读取训练指标...")
    metrics = parse_results(model_info["results"])
    if metrics:
        print(f"   📈 Epochs: {metrics.get('epochs', 'N/A')}")
        print(f"   📈 mAP50: {metrics.get('mAP50', 0):.4f}")
        print(f"   📈 mAP50-95: {metrics.get('mAP50_95', 0):.4f}")
        print(f"   📈 Precision: {metrics.get('precision', 0):.4f}")
        print(f"   📈 Recall: {metrics.get('recall', 0):.4f}")

    # 3. 创建 models 目录
    print("\n3. 复制模型文件...")
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)

    # 生成版本名称
    version_name = train_dir.name  # 例如: custom_m_1770740151
    target_path = models_dir / f"{version_name}.pt"

    # 复制文件
    try:
        shutil.copy2(best_pt, target_path)
        print(f"   ✅ 复制成功: {target_path}")
    except Exception as e:
        print(f"   ❌ 复制失败: {e}")
        return False

    # 4. 保存模型信息文件
    info_file = models_dir / f"{version_name}.json"
    model_info_data = {
        "version_name": version_name,
        "created_at": datetime.now().isoformat(),
        "train_dir": str(train_dir),
        "metrics": metrics,
        "model_path": str(target_path),
        "is_active": False
    }

    try:
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(model_info_data, f, indent=2, ensure_ascii=False)
        print(f"   ✅ 信息文件: {info_file}")
    except Exception as e:
        print(f"   ⚠️ 保存信息失败: {e}")

    # 5. 创建激活脚本
    print("\n4. 创建激活脚本...")

    # Windows 批处理脚本
    bat_script = f"""@echo off
echo 激活模型: {version_name}
echo 请在后端刷新后，在网页上点击"激活"按钮
pause
"""

    activate_bat = models_dir / f"activate_{version_name}.bat"
    activate_bat.write_text(bat_script, encoding='gbk')
    print(f"   ✅ {activate_bat}")

    # Python 激活脚本（直接修改数据库）
    py_script = f'''
import sys
sys.path.insert(0, "backend")

try:
    from app.config import supabase

    # 停用所有模型
    supabase.table("model_versions").update({{"is_active": False}}).neq("id", 0).execute()

    # 插入新模型记录
    data = {{
        "version_name": "{version_name}",
        "training_data_count": 1230,
        "map50": {metrics.get('mAP50', 0)},
        "map75": {metrics.get('mAP75', 0)},
        "map50_95": {metrics.get('mAP50_95', 0)},
        "precision": {metrics.get('precision', 0)},
        "recall": {metrics.get('recall', 0)},
        "model_size": "m",
        "model_path": null,
        "local_path": "{target_path.absolute().as_posix()}",
        "is_active": True,
        "training_status": "completed",
        "completed_at": "{datetime.now().isoformat()}"
    }}

    result = supabase.table("model_versions").insert(data).execute()
    print("✅ 模型已激活:", "{version_name}")

except Exception as e:
    print("❌ 激活失败:", e)
    print("请手动在网页上点击激活按钮")
'''

    activate_py = models_dir / f"activate_{version_name}.py"
    activate_py.write_text(py_script, encoding='utf-8')
    print(f"   ✅ {activate_py}")

    # 6. 总结
    print("\n" + "=" * 60)
    print("✅ 模型复制完成!")
    print("=" * 60)
    print(f"\n模型名称: {version_name}")
    print(f"模型路径: {target_path.absolute()}")
    print(f"\n下一步:")
    print(f"  1. 重启后端服务 (Ctrl+C 然后 python -m app.main)")
    print(f"  2. 刷新网页 http://localhost:5173/training")
    print(f"  3. 点击'激活'按钮使用新模型")
    print(f"\n或直接运行激活脚本:")
    print(f"  python {activate_py}")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = copy_model()
    sys.exit(0 if success else 1)