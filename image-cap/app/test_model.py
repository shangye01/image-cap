# test_model.py
from ultralytics import YOLO
from PIL import Image
import sys


def test_model():
    # 测试默认模型
    print("🧪 测试 YOLOv8n 模型...")
    try:
        model = YOLO("yolov8n.pt")
        print(f"✅ 模型加载成功: {model.task}")

        # 测试推理
        # 创建一个简单的测试图片或使用你的图片
        test_image = "path/to/your/test/image.jpg"  # 替换为你的测试图片

        print(f"🔍 测试图片: {test_image}")
        results = model(test_image, conf=0.15, verbose=True)

        print(f"\n📊 检测结果:")
        print(f"  原始检测数: {len(results[0].boxes)}")

        for i, box in enumerate(results[0].boxes):
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            print(f"  [{i}] {model.names[cls]}: {conf:.3f}")

        if len(results[0].boxes) == 0:
            print("\n⚠️ 没有检测到任何目标！")
            print("建议：")
            print("1. 降低 conf 阈值 (当前 0.15)")
            print("2. 检查图片是否包含 COCO 数据集的 80 个类别")
            print("3. 尝试使用更大的模型 (yolov8s/m/l)")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_model()