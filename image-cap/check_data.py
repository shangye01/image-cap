from pathlib import Path


def check_dataset():
    base = Path("datasets/custom")

    print("=" * 50)
    print("📊 数据集检查")
    print("=" * 50)

    # 检查目录结构
    dirs = {
        "训练图片": base / "train/images",
        "训练标注": base / "train/labels",
        "验证图片": base / "val/images",
        "验证标注": base / "val/labels",
    }

    stats = {}
    for name, path in dirs.items():
        if path.exists():
            if "images" in str(path):
                count = len(list(path.glob("*.jpg"))) + len(list(path.glob("*.png")))
            else:
                count = len(list(path.glob("*.txt")))
            stats[name] = count
            print(f"✅ {name}: {count} 个文件")
        else:
            print(f"❌ {name}: 目录不存在")
            return False

    # 检查类别文件
    classes_file = base / "classes.txt"
    if classes_file.exists():
        classes = classes_file.read_text().strip().split('\n')
        print(f"\n📋 类别 ({len(classes)} 个):")
        for i, c in enumerate(classes):
            print(f"  {i}: {c}")
    else:
        print("\n⚠️ 未找到 classes.txt")

    # 数据量评估
    train_count = stats.get("训练图片", 0)
    val_count = stats.get("验证图片", 0)

    print(f"\n📈 数据量评估:")
    print(f"  训练集: {train_count} 张")
    print(f"  验证集: {val_count} 张")
    print(f"  验证比例: {val_count / (train_count + val_count) * 100:.1f}%")

    if train_count < 50:
        print("\n⚠️ 警告: 训练集太少 (< 50)，效果可能不佳")
    elif train_count < 200:
        print("\n⚠️ 训练集偏少，建议启用强数据增强")
    else:
        print("\n✅ 数据量充足")

    # 检查标注文件是否匹配
    train_imgs = set(p.stem for p in (base / "train/images").glob("*.*"))
    train_txts = set(p.stem for p in (base / "train/labels").glob("*.txt"))

    missing_labels = train_imgs - train_txts
    if missing_labels:
        print(f"\n⚠️ {len(missing_labels)} 张图片缺少标注文件")
        print(f"  例如: {list(missing_labels)[:3]}")

    print("\n" + "=" * 50)
    print("如果以上都显示 ✅，就可以开始训练了！")
    print("=" * 50)

    return train_count > 0 and val_count > 0


if __name__ == "__main__":
    check_dataset()