import json
import urllib.request
from pathlib import Path
import shutil
from tqdm import tqdm
import multiprocessing as mp

# 你想训练的类别（COCO类别ID映射）
COCO_CLASSES = {
    "person": 1,
    "bicycle": 2,
    "car": 3,
    "motorcycle": 4,
    "airplane": 5,
    "bus": 6,
    "train": 7,
    "truck": 8,
    "boat": 9,
    "traffic light": 10,
    "fire hydrant": 11,
    "stop sign": 13,
    "parking meter": 14,
    "bench": 15,
    "bird": 16,
    "cat": 17,
    "dog": 18,
    "horse": 19,
    "sheep": 20,
    "cow": 21,
    "elephant": 22,
    "bear": 23,
    "zebra": 24,
    "giraffe": 25,
}


def download_image(args):
    """下载单张图片"""
    img_url, save_path = args
    try:
        urllib.request.urlretrieve(img_url, save_path)
        return True
    except Exception as e:
        print(f"下载失败 {img_url}: {e}")
        return False


def create_coco_subset(
        target_classes=["person", "car", "dog", "cat"],
        max_images_per_class=1000,
        num_workers=4
):
    """
    创建COCO子集

    参数:
        target_classes: 想要的类别名称列表
        max_images_per_class: 每个类别最多多少张图片
        num_workers: 并行下载进程数
    """

    data_dir = Path("coco_subset")
    data_dir.mkdir(exist_ok=True)

    # 下载标注文件
    anno_url = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
    anno_zip = data_dir / "annotations.zip"

    if not (data_dir / "annotations").exists():
        print("下载标注文件...")
        urllib.request.urlretrieve(anno_url, anno_zip)
        import zipfile
        with zipfile.ZipFile(anno_zip, 'r') as z:
            z.extractall(data_dir)

    # 加载标注
    print("加载COCO标注...")
    with open(data_dir / "annotations/instances_train2017.json", 'r') as f:
        train_data = json.load(f)
    with open(data_dir / "annotations/instances_val2017.json", 'r') as f:
        val_data = json.load(f)

    # 获取目标类别ID
    target_cat_ids = [COCO_CLASSES[c] for c in target_classes if c in COCO_CLASSES]
    print(f"目标类别: {target_classes}")
    print(f"类别IDs: {target_cat_ids}")

    # 创建类别映射（COCO ID -> YOLO ID）
    cat_id_to_yolo = {cat_id: idx for idx, cat_id in enumerate(target_cat_ids)}

    # 保存类别名称文件
    with open("datasets/custom/classes.txt", 'w') as f:
        f.write('\n'.join(target_classes))
    print(f"✅ 类别文件已保存: datasets/custom/classes.txt")

    # 处理数据集（训练集和验证集）
    for split, coco_data in [("train", train_data), ("val", val_data)]:
        print(f"\n处理 {split} 集...")

        # 过滤包含目标类别的图片
        cat_to_imgs = {cat_id: set() for cat_id in target_cat_ids}
        for ann in coco_data['annotations']:
            if ann['category_id'] in target_cat_ids:
                cat_to_imgs[ann['category_id']].add(ann['image_id'])

        # 选择图片（每个类别最多max_images_per_class张）
        selected_imgs = set()
        for cat_id, img_ids in cat_to_imgs.items():
            selected = list(img_ids)[:max_images_per_class]
            selected_imgs.update(selected)
            print(f"  类别 {cat_id}: 选择 {len(selected)} 张图片")

        print(f"总共选择 {len(selected_imgs)} 张图片")

        # 创建输出目录
        out_img_dir = Path(f"datasets/custom/{split}/images")
        out_lbl_dir = Path(f"datasets/custom/{split}/labels")
        out_img_dir.mkdir(parents=True, exist_ok=True)
        out_lbl_dir.mkdir(parents=True, exist_ok=True)

        # 构建图片信息字典
        img_dict = {img['id']: img for img in coco_data['images']}

        # 按图片分组标注
        img_to_anns = {img_id: [] for img_id in selected_imgs}
        for ann in coco_data['annotations']:
            if ann['image_id'] in selected_imgs and ann['category_id'] in target_cat_ids:
                img_to_anns[ann['image_id']].append(ann)

        # 准备下载任务
        download_tasks = []
        base_url = "http://images.cocodataset.org/zips/train2017" if split == "train" else "http://images.cocodataset.org/zips/val2017"

        for img_id in selected_imgs:
            img_info = img_dict[img_id]
            img_filename = img_info['file_name']
            img_path = out_img_dir / img_filename

            # 构建图片URL（COCO图片直接下载链接）
            img_url = f"http://images.cocodataset.org/{'train2017' if split == 'train' else 'val2017'}/{img_filename}"

            if not img_path.exists():
                download_tasks.append((img_url, str(img_path)))

            # 创建YOLO格式标注
            yolo_lines = []
            for ann in img_to_anns[img_id]:
                # COCO bbox是左上角坐标，YOLO需要中心点
                x, y, w, h = ann['bbox']
                img_w, img_h = img_info['width'], img_info['height']

                # 转换为YOLO格式（归一化）
                x_center = (x + w / 2) / img_w
                y_center = (y + h / 2) / img_h
                w_norm = w / img_w
                h_norm = h / img_h

                # 限制在0-1范围内
                x_center = max(0, min(1, x_center))
                y_center = max(0, min(1, y_center))
                w_norm = max(0, min(1, w_norm))
                h_norm = max(0, min(1, h_norm))

                yolo_id = cat_id_to_yolo[ann['category_id']]
                yolo_lines.append(f"{yolo_id} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}")

            # 保存标注文件
            txt_path = out_lbl_dir / (Path(img_filename).stem + '.txt')
            txt_path.write_text('\n'.join(yolo_lines))

        # 并行下载图片
        if download_tasks:
            print(f"下载 {len(download_tasks)} 张图片...")
            with mp.Pool(num_workers) as pool:
                list(tqdm(
                    pool.imap(download_image, download_tasks),
                    total=len(download_tasks),
                    desc=f"下载{split}图片"
                ))

    print("\n✅ COCO子集准备完成!")
    print(f"数据集位置: datasets/custom/")
    print("现在可以刷新训练页面开始训练了")


if __name__ == "__main__":
    # 示例：下载 person, car, dog, cat 四个类别，每类最多500张
    create_coco_subset(
        target_classes=["person", "car", "dog", "cat"],
        max_images_per_class=500,
        num_workers=4
    )