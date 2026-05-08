# app/core/dataset_manager.py
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import logging

from app.config import supabase

logger = logging.getLogger(__name__)

# 本地缓存目录
LOCAL_DATASET_DIR = Path("./datasets")
LOCAL_DATASET_DIR.mkdir(parents=True, exist_ok=True)


class DatasetInfo:
    """数据集信息"""

    def __init__(self, id: str, name: str, storage_prefix: str = "", is_local: bool = False):
        self.id = id
        self.name = name
        self.storage_prefix = storage_prefix
        self.is_local = is_local
        self.local_path: Optional[Path] = None
        self.stats: Dict = {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "dataset_id": self.id,
            "name": self.name,
            "storage_prefix": self.storage_prefix,
            "is_local": self.is_local,
            "local_path": str(self.local_path) if self.local_path else None,
            "stats": self.stats
        }


class DatasetManager:
    """管理多个数据集，支持从 Storage 下载和切换"""

    def __init__(self):
        self.datasets: Dict[str, DatasetInfo] = {}
        self.active_dataset_id: Optional[str] = None
        self._scan_local_datasets()
        self._discover_storage_datasets()

    def _scan_local_datasets(self):
        """扫描本地已有的数据集"""
        if not LOCAL_DATASET_DIR.exists():
            return

        for item in LOCAL_DATASET_DIR.iterdir():
            if item.is_dir() and (item / "data.yaml").exists():
                dataset_id = item.name
                self.datasets[dataset_id] = DatasetInfo(
                    id=dataset_id,
                    name=dataset_id,
                    is_local=True
                )
                self.datasets[dataset_id].local_path = item

                train_imgs = list((item / "train" / "images").glob("*")) if (item / "train" / "images").exists() else []
                val_imgs = list((item / "val" / "images").glob("*")) if (item / "val" / "images").exists() else []
                self.datasets[dataset_id].stats = {
                    "train_images": len(train_imgs),
                    "val_images": len(val_imgs),
                    "total": len(train_imgs) + len(val_imgs)
                }

                logger.info(f"发现本地数据集: {dataset_id} ({len(train_imgs)} train, {len(val_imgs)} val)")

    def _discover_storage_datasets(self):
        """发现 Storage 中的数据集 - 支持多种结构"""
        try:
            root_items = supabase.storage.from_("datasets").list(
                path=None,
                options={"limit": 100, "offset": 0}
            )

            logger.info(f"Storage 根目录扫描到 {len(root_items)} 个对象")

            root_files = [item.get("name") for item in root_items if item.get("id")]
            root_folders = [item.get("name") for item in root_items if not item.get("id")]

            # 检查根目录是否有标准YOLO结构 (train/ 和 val/ 文件夹)
            has_train_val = "train" in root_folders and "val" in root_folders
            has_data_yaml = "data.yaml" in root_files

            if has_train_val or has_data_yaml:
                if "default" not in self.datasets:
                    self.datasets["default"] = DatasetInfo(
                        id="default",
                        name="默认数据集 (根目录)",
                        storage_prefix="",
                        is_local=False
                    )
                    logger.info("发现 Storage 根目录数据集 (default)")

            # 扫描子目录（projects/ 和 annotations/ 等）
            for item in root_items:
                name = item.get("name", "")
                if not item.get("id") and name not in ["train", "val", "images", "labels"]:
                    try:
                        sub_items = supabase.storage.from_("datasets").list(
                            path=name,
                            options={"limit": 100}
                        )
                        sub_names = [sub.get("name") for sub in sub_items]
                        sub_folders = [sub.get("name") for sub in sub_items if not sub.get("id")]

                        is_dataset = (
                                "data.yaml" in sub_names or
                                ("train" in sub_folders and "val" in sub_folders)
                        )

                        if is_dataset:
                            dataset_id = name
                            if dataset_id not in self.datasets:
                                display_name = name
                                if name == "projects":
                                    display_name = "项目数据集"
                                elif name == "annotations":
                                    display_name = "标注数据集"

                                self.datasets[dataset_id] = DatasetInfo(
                                    id=dataset_id,
                                    name=display_name,
                                    storage_prefix=name,
                                    is_local=False
                                )
                                logger.info(f"发现 Storage 数据集: {dataset_id}")
                    except Exception as e:
                        logger.warning(f"检查子目录 {name} 失败: {e}")

        except Exception as e:
            logger.warning(f"扫描 Storage 数据集失败: {e}")

    def list_available_datasets(self) -> List[dict]:
        return [d.to_dict() for d in self.datasets.values()]

    def get_dataset_path(self, dataset_id: str) -> Optional[Path]:
        if dataset_id not in self.datasets:
            return None

        info = self.datasets[dataset_id]

        if dataset_id == "default" and not info.local_path:
            return None

        if info.local_path and info.local_path.exists():
            return info.local_path

        return self._download_from_storage(dataset_id)

    def _download_from_storage(self, dataset_id: str) -> Optional[Path]:
        info = self.datasets.get(dataset_id)
        if not info:
            return None

        local_path = LOCAL_DATASET_DIR / dataset_id
        prefix = info.storage_prefix

        try:
            logger.info(f"开始下载数据集 {dataset_id} 从 Storage (prefix: '{prefix}')...")

            local_path.mkdir(parents=True, exist_ok=True)

            # 下载 data.yaml
            yaml_remote = f"{prefix}/data.yaml" if prefix else "data.yaml"
            try:
                self._download_file("datasets", yaml_remote, local_path / "data.yaml")
            except Exception:
                logger.warning(f"data.yaml 不存在，将尝试生成")

            # 下载 classes.txt（可选）
            try:
                classes_remote = f"{prefix}/classes.txt" if prefix else "classes.txt"
                self._download_file("datasets", classes_remote, local_path / "classes.txt")
            except Exception:
                logger.warning("classes.txt 不存在")

            # 下载 train 目录
            train_prefix = f"{prefix}/train" if prefix else "train"
            train_local = local_path / "train"
            self._download_folder("datasets", f"{train_prefix}/images", train_local / "images")
            self._download_folder("datasets", f"{train_prefix}/labels", train_local / "labels")

            # 下载 val 目录
            val_prefix = f"{prefix}/val" if prefix else "val"
            val_local = local_path / "val"
            self._download_folder("datasets", f"{val_prefix}/images", val_local / "images")
            self._download_folder("datasets", f"{val_prefix}/labels", val_local / "labels")

            # 验证结构
            if not (local_path / "train" / "images").exists():
                logger.error(f"数据集 {dataset_id} 结构不完整")
                shutil.rmtree(local_path)
                return None

            # 如果没有 data.yaml，生成一个
            if not (local_path / "data.yaml").exists():
                self._generate_data_yaml(local_path)

            info.local_path = local_path
            info.is_local = True

            train_images = list((local_path / "train" / "images").glob("*"))
            val_images = list((local_path / "val" / "images").glob("*"))
            info.stats = {
                "train_images": len(train_images),
                "val_images": len(val_images),
                "total": len(train_images) + len(val_images)
            }

            logger.info(f"数据集 {dataset_id} 下载完成: {info.stats}")
            return local_path

        except Exception as e:
            logger.error(f"下载数据集 {dataset_id} 失败: {e}")
            if local_path.exists():
                shutil.rmtree(local_path)
            return None

    def _generate_data_yaml(self, dataset_dir: Path):
        """自动生成 data.yaml"""
        classes_file = dataset_dir / "classes.txt"
        if classes_file.exists():
            with open(classes_file, 'r') as f:
                names = [l.strip() for l in f if l.strip()]
        else:
            labels_dir = dataset_dir / "train" / "labels"
            class_ids = set()
            if labels_dir.exists():
                for f in labels_dir.glob("*.txt"):
                    with open(f) as file:
                        for line in file:
                            parts = line.strip().split()
                            if parts:
                                class_ids.add(int(parts[0]))
            names = [f"class_{i}" for i in sorted(class_ids)] if class_ids else ["object"]

        yaml_content = f"""path: {dataset_dir.absolute()}
train: train/images
val: val/images
nc: {len(names)}
names: {names}
"""
        yaml_path = dataset_dir / "data.yaml"
        with open(yaml_path, "w") as f:
            f.write(yaml_content)
        logger.info(f"生成 data.yaml: {yaml_path}")

    def _download_file(self, bucket: str, remote_path: str, local_path: Path):
        try:
            file_data = supabase.storage.from_(bucket).download(remote_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, "wb") as f:
                if isinstance(file_data, bytes):
                    f.write(file_data)
                else:
                    f.write(file_data.encode())
            logger.debug(f"下载文件: {remote_path} -> {local_path}")
        except Exception as e:
            logger.error(f"下载文件失败 {remote_path}: {e}")
            raise

    def _download_folder(self, bucket: str, remote_path: str, local_path: Path):
        local_path.mkdir(parents=True, exist_ok=True)
        try:
            items = supabase.storage.from_(bucket).list(
                path=remote_path,
                options={"limit": 100}
            )
            for item in items:
                name = item.get("name")
                if not name:
                    continue
                item_local = local_path / name
                if not item.get("id"):
                    self._download_folder(bucket, f"{remote_path}/{name}", item_local)
                else:
                    file_data = supabase.storage.from_(bucket).download(f"{remote_path}/{name}")
                    with open(item_local, "wb") as f:
                        if isinstance(file_data, bytes):
                            f.write(file_data)
                        else:
                            f.write(file_data.encode())
        except Exception as e:
            logger.warning(f"下载文件夹 {remote_path} 失败: {e}")

    def switch_dataset(self, dataset_id: str) -> bool:
        if dataset_id == "default" and dataset_id in self.datasets:
            self.active_dataset_id = dataset_id
            logger.info("鍒囨崲鍒板熀纭€鏁版嵁闆? default")
            return True
        path = self.get_dataset_path(dataset_id)
        if path and path.exists():
            self.active_dataset_id = dataset_id
            logger.info(f"切换到数据集: {dataset_id}, 路径: {path}")
            return True
        return False

    def get_active_dataset_path(self) -> Optional[Path]:
        if self.active_dataset_id:
            return self.get_dataset_path(self.active_dataset_id)
        return None

    def is_cached(self, dataset_id: str) -> bool:
        info = self.datasets.get(dataset_id)
        if not info:
            return False
        return info.local_path is not None and info.local_path.exists()

    def get_cache_path(self, dataset_id: str) -> Optional[Path]:
        info = self.datasets.get(dataset_id)
        if info and info.local_path and info.local_path.exists():
            return info.local_path
        return None

    def cleanup(self, dataset_id: str = None):
        if dataset_id:
            info = self.datasets.get(dataset_id)
            if info and info.local_path and info.local_path.exists():
                shutil.rmtree(info.local_path)
                info.local_path = None
                info.is_local = False
                logger.info(f"已清理数据集缓存: {dataset_id}")
        else:
            for item in LOCAL_DATASET_DIR.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
            for info in self.datasets.values():
                info.local_path = None
                info.is_local = False
            logger.info("已清理所有数据集缓存")


dataset_manager = DatasetManager()
