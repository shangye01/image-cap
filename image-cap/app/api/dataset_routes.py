# api/dataset_routes.py
import supabase
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form, Header
from pydantic import BaseModel, Field
from typing import List, Optional, Annotated
import os
import json
import zipfile
import shutil
import io
import uuid
import re




from datetime import datetime
from pathlib import Path
import logging  #
router = APIRouter(prefix="/api/dataset", tags=["dataset"])


# 关键修复：导入 supabase 客户端
from app.config import supabase

logger = logging.getLogger(__name__)
ANNOTATION_EXPORTS_TABLE = "annotation_exports"
# ===== 数据模型 =====

class AnnotationData(BaseModel):
    task_id: str
    image_url: str
    image_storage_path: Optional[str] = None
    annotations: List[dict]
    label_map: dict


class DatasetMergeRequest(BaseModel):
    project_id: str
    dataset_name: str
    description: Optional[str] = ""
    annotation_tasks: List[str]
    original_dataset_path: Optional[str] = None


class DatasetStatusResponse(BaseModel):
    ready: bool
    message: str
    dataset_id: Optional[str] = None
    stats: Optional[dict] = None
    storage_path: Optional[str] = None
    created_at: Optional[str] = None


class ProcessFromStorageRequest(BaseModel):
    project_id: str
    dataset_name: str
    storage_path: str
    bucket: str = "datasets"
    original_filename: Optional[str] = None
    file_size: Optional[int] = None


class ProcessingStatus(BaseModel):
    task_id: str
    status: str
    percent: int
    message: str
    detail: Optional[str] = None
    result: Optional[dict] = None


# ===== 全局状态 =====

# 内存存储数据集状态（生产环境应使用 Redis）
dataset_registry = {}

# 处理任务状态存储
processing_tasks: dict = {}


def _safe_storage_segment(value: str, fallback: str = "item") -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", (value or "").strip())
    normalized = normalized.strip("-._")
    return normalized or fallback


# ===== 辅助函数 =====
# 添加 get_supabase_client 函数
def get_supabase_client():
    """获取 Supabase 客户端"""
    try:
        # 尝试导入全局客户端
        from app.config import supabase as global_supabase
        if global_supabase is not None:
            return global_supabase
    except:
        pass

    # 创建新客户端
    from supabase import create_client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError("Supabase 环境变量未设置")

    return create_client(supabase_url, supabase_key)

def format_file_size(bytes_size: int) -> str:
    """
    格式化文件大小
    """
    if bytes_size == 0:
        return "0 Bytes"
    k = 1024
    sizes = ["Bytes", "KB", "MB", "GB"]
    i = 0
    while bytes_size >= k and i < len(sizes) - 1:
        bytes_size /= k
        i += 1
    return f"{bytes_size:.2f} {sizes[i]}"


def update_status(task_id: str, status: str, percent: int, message: str, detail: str = "",
                  result: Optional[dict] = None):
    """
    更新处理任务状态
    """
    processing_tasks[task_id] = {
        "task_id": task_id,
        "status": status,
        "percent": percent,
        "message": message,
        "detail": detail,
        "result": result
    }
    print(f"[{task_id}] [{status}] {message} ({percent}%) {detail}")


def find_dataset_root(directory: str) -> Optional[str]:
    """
    查找包含 images/ 和 labels/ 的目录
    """
    # 首先检查根目录
    if os.path.exists(os.path.join(directory, "images")) and \
            os.path.exists(os.path.join(directory, "labels")):
        return directory

    # 递归检查子目录（最多2层）
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            if os.path.exists(os.path.join(item_path, "images")) and \
                    os.path.exists(os.path.join(item_path, "labels")):
                return item_path

            # 再深入一层
            for subitem in os.listdir(item_path):
                subitem_path = os.path.join(item_path, subitem)
                if os.path.isdir(subitem_path):
                    if os.path.exists(os.path.join(subitem_path, "images")) and \
                            os.path.exists(os.path.join(subitem_path, "labels")):
                        return subitem_path

    return None


def analyze_local_dataset(directory: str) -> dict:
    """
    分析本地数据集结构
    """
    structure = {
        "images": [],
        "labels": [],
        "labels_dir": None,
        "root_dir": directory
    }

    for root, dirs, files in os.walk(directory):
        # 跳过 dataset 子目录（避免递归）
        if "dataset" in root.split(os.sep):
            continue

        # 找到 images 文件夹
        if "images" in root.split(os.sep):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
                    structure["images"].append(os.path.join(root, file))

        # 找到 labels 文件夹
        if "labels" in root.split(os.sep):
            if structure["labels_dir"] is None:
                structure["labels_dir"] = root
            for file in files:
                if file.endswith('.txt'):
                    structure["labels"].append(os.path.join(root, file))

    return structure


# ===== 后台处理任务 =====

async def recalculate_stats(storage_path: str, bucket: str = "datasets") -> dict:
    """
    从 Storage 文件夹重新计算数据集统计信息（支持分页）
    修复：正确使用 Supabase Python 客户端的 limit/offset 参数 [^4^]
    """
    try:
        supabase_client = get_supabase_client()

        # 解析路径
        clean_path = storage_path.strip("/")

        if clean_path == bucket or clean_path == "":
            folder_name = ""
            logger.info(f"从 bucket 根目录统计")
        elif clean_path.startswith(f"{bucket}/"):
            folder_name = clean_path[len(bucket) + 1:].split("/")[0]
        else:
            folder_name = clean_path.split("/")[0]

        base_path = f"{folder_name}/" if folder_name else ""
        logger.info(f"开始统计: folder_name='{folder_name}', base_path='{base_path}'")

        # ========== 修复：正确的分页参数传递方式 ==========
        async def list_all_files(path: str) -> list:
            """获取文件夹下所有文件，处理分页（修正参数传递）"""
            all_files = []
            path = path.lstrip("/")
            offset = 0
            limit = 100  # Supabase 默认最大 100

            while True:
                try:
                    # 正确方式：第二个参数是 options 字典
                    result = supabase_client.storage.from_(bucket).list(
                        path,
                        {
                            "limit": limit,
                            "offset": offset,
                            "sortBy": {"column": "name", "order": "asc"}
                        }
                    )

                    if not result:
                        break

                    all_files.extend(result)

                    # 如果返回数量小于 limit，说明已经取完
                    if len(result) < limit:
                        break

                    offset += limit
                    logger.info(f"分页获取: path='{path}', offset={offset}, 已获取 {len(all_files)} 条")

                except Exception as e:
                    logger.warning(f"列出 '{path}' 失败: {e}")
                    break

            logger.info(f"路径 '{path}' 总共列出 {len(all_files)} 项")
            return all_files

        # 判断是否是文件夹
        def is_folder(item: dict) -> bool:
            name = item.get('name', '')
            has_id = item.get('id') is not None
            no_ext = '.' not in name
            return has_id or no_ext

        # 1. 获取 train/images
        train_count = 0
        try:
            train_list = await list_all_files(f"{base_path}train")
            logger.info(f"train 文件夹内容数量: {len(train_list)}")

            if not train_list:
                logger.warning(f"train 文件夹为空")
            else:
                # 查找 images 子文件夹
                images_folder = next((f for f in train_list
                                      if f.get('name') == 'images' and is_folder(f)), None)

                if images_folder:
                    logger.info(f"找到 images 子文件夹，进入统计...")
                    images_list = await list_all_files(f"{base_path}train/images")

                    # 统计所有图片（支持多种格式）
                    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.tiff', '.tif')
                    train_files = [f for f in images_list
                                   if f.get('name', '').lower().endswith(image_extensions)]
                    train_count = len(train_files)
                    logger.info(f"train/images: {train_count} 张图片 (共 {len(images_list)} 个文件)")
                else:
                    # 直接统计 train 下的图片
                    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.tiff', '.tif')
                    train_files = [f for f in train_list
                                   if f.get('name', '').lower().endswith(image_extensions)]
                    train_count = len(train_files)
                    logger.info(f"train 目录直接: {train_count} 张图片")
        except Exception as e:
            logger.error(f"统计 train 失败: {e}")

        # 2. 获取 val/images
        val_count = 0
        try:
            val_list = await list_all_files(f"{base_path}val")
            logger.info(f"val 文件夹内容数量: {len(val_list)}")

            if val_list:
                images_folder = next((f for f in val_list
                                      if f.get('name') == 'images' and is_folder(f)), None)
                if images_folder:
                    logger.info(f"找到 val/images 子文件夹，进入统计...")
                    images_list = await list_all_files(f"{base_path}val/images")

                    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.tiff', '.tif')
                    val_files = [f for f in images_list
                                 if f.get('name', '').lower().endswith(image_extensions)]
                    val_count = len(val_files)
                    logger.info(f"val/images: {val_count} 张图片 (共 {len(images_list)} 个文件)")
        except Exception as e:
            logger.error(f"统计 val 失败: {e}")

        # 3. 读取 classes.txt
        classes = []
        classes_paths = [
            f"{base_path}train/classes.txt",
            f"{base_path}classes.txt",
            "train/classes.txt",
            "classes.txt"
        ]

        for classes_path in classes_paths:
            try:
                classes_path = classes_path.lstrip("/")
                file_response = supabase_client.storage.from_(bucket).download(classes_path)
                if file_response:
                    content = file_response.decode('utf-8') if isinstance(file_response, bytes) else file_response
                    classes = [line.strip() for line in content.split('\n') if line.strip()]
                    logger.info(f"从 {classes_path} 读取 {len(classes)} 个类别")
                    break
            except Exception as e:
                logger.debug(f"读取 {classes_path} 失败: {e}")

        # 4. 从 labels 推断类别（备用）
        if not classes:
            try:
                labels_list = await list_all_files(f"{base_path}train/labels")
                if labels_list:
                    class_ids = set()
                    for label_file in labels_list[:100]:  # 最多检查100个标注文件
                        if not label_file.get('name', '').endswith('.txt'):
                            continue
                        try:
                            label_data = supabase_client.storage.from_(bucket).download(
                                f"{base_path}train/labels/{label_file['name']}"
                            )
                            if label_data:
                                content = label_data.decode('utf-8') if isinstance(label_data, bytes) else label_data
                                for line in content.split('\n'):
                                    parts = line.strip().split()
                                    if parts and parts[0].isdigit():
                                        class_ids.add(int(parts[0]))
                        except:
                            continue
                    classes = [f"class_{i}" for i in sorted(class_ids)]
                    logger.info(f"从 labels 推断 {len(classes)} 个类别")
            except Exception as e:
                logger.warning(f"从 labels 推断失败: {e}")

        stats = {
            "train": train_count,
            "val": val_count,
            "total": train_count + val_count,
            "classes": len(classes),
            "class_names": classes
        }

        logger.info(f"统计完成: {stats}")
        return stats

    except Exception as e:
        logger.error(f"重新计算 stats 失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"train": 0, "val": 0, "total": 0, "classes": 0, "class_names": []}


async def process_dataset_task(task_id: str, request: ProcessFromStorageRequest):
    """
    后台处理数据集任务
    """
    temp_dir = None

    try:
        # 阶段 1: 下载文件 (0-30%)
        update_status(task_id, "uploading", 5, "正在连接 Storage...", f"路径: {request.storage_path}")

        from supabase import create_client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        supabase = create_client(supabase_url, supabase_key)

        update_status(task_id, "uploading", 10, "正在下载 ZIP 文件...", "")

        try:
            zip_data = supabase.storage.from_(request.bucket).download(request.storage_path)
            update_status(task_id, "uploading", 25, "下载完成", f"大小: {format_file_size(len(zip_data))}")
        except Exception as e:
            raise Exception(f"无法从 Storage 下载文件: {str(e)}")

        # 阶段 2: 解压文件 (30-50%)
        update_status(task_id, "extracting", 35, "创建临时目录...", "")

        temp_dir = f"/tmp/dataset_process_{task_id}"
        os.makedirs(temp_dir, exist_ok=True)

        zip_path = os.path.join(temp_dir, "dataset.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_data)

        update_status(task_id, "extracting", 40, "解压 ZIP 文件...", "")

        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        # 统计解压后的文件
        file_count = 0
        for root, dirs, files in os.walk(extract_dir):
            file_count += len(files)

        update_status(task_id, "extracting", 50, "解压完成", f"共 {file_count} 个文件")

        # 阶段 3: 分析数据集 (50-65%)
        update_status(task_id, "analyzing", 55, "查找数据集结构...", "")

        dataset_root = find_dataset_root(extract_dir)

        if not dataset_root:
            raise Exception("ZIP 文件中未找到有效的数据集结构（需要包含 images/ 和 labels/ 文件夹）")

        update_status(task_id, "analyzing", 58, "找到数据集根目录",
                      f"路径: {os.path.relpath(dataset_root, extract_dir)}")

        structure = analyze_local_dataset(dataset_root)

        if not structure["images"]:
            raise Exception("未找到图片文件")

        if not structure["labels"]:
            raise Exception("未找到标签文件")

        update_status(task_id, "analyzing", 62, "分析文件结构",
                      f"图片: {len(structure['images'])}, 标签: {len(structure['labels'])}")

        # 读取类别信息
        classes = []
        classes_file = os.path.join(structure["root_dir"], "classes.txt")
        if os.path.exists(classes_file):
            with open(classes_file, 'r') as f:
                classes = [line.strip() for line in f if line.strip()]
            update_status(task_id, "analyzing", 65, "读取类别信息", f"类别: {classes}")

        # 阶段 4: 创建标准 YOLO 结构 (65-85%)
        update_status(task_id, "packaging", 70, "创建标准 YOLO 结构...", "")

        dataset_dir = os.path.join(temp_dir, "dataset")
        train_images_dir = os.path.join(dataset_dir, "train", "images")
        train_labels_dir = os.path.join(dataset_dir, "train", "labels")
        val_images_dir = os.path.join(dataset_dir, "val", "images")
        val_labels_dir = os.path.join(dataset_dir, "val", "labels")

        for d in [train_images_dir, train_labels_dir, val_images_dir, val_labels_dir]:
            os.makedirs(d, exist_ok=True)

        # 分配训练集和验证集 (80/20)
        import random
        random.seed(42)
        all_images = structure["images"]
        random.shuffle(all_images)
        split_idx = int(len(all_images) * 0.8)
        train_images = all_images[:split_idx]
        val_images = all_images[split_idx:]

        update_status(task_id, "packaging", 72, "分配数据集",
                      f"训练集: {len(train_images)}, 验证集: {len(val_images)}")

        # 复制训练集
        copied = 0
        for img_path in train_images:
            img_name = os.path.basename(img_path)
            label_name = os.path.splitext(img_name)[0] + ".txt"
            label_path = os.path.join(structure["labels_dir"], label_name)

            shutil.copy2(img_path, os.path.join(train_images_dir, img_name))
            if os.path.exists(label_path):
                shutil.copy2(label_path, os.path.join(train_labels_dir, label_name))

            copied += 1
            if copied % 100 == 0:
                update_status(task_id, "packaging", 72 + int((copied / len(train_images)) * 5),
                              "复制训练集...", f"{copied}/{len(train_images)}")

        # 复制验证集
        for img_path in val_images:
            img_name = os.path.basename(img_path)
            label_name = os.path.splitext(img_name)[0] + ".txt"
            label_path = os.path.join(structure["labels_dir"], label_name)

            shutil.copy2(img_path, os.path.join(val_images_dir, img_name))
            if os.path.exists(label_path):
                shutil.copy2(label_path, os.path.join(val_labels_dir, label_name))

        update_status(task_id, "packaging", 78, "复制验证集完成", f"共 {len(val_images)} 张")

        # 如果没有 classes.txt，从标签推断
        if not classes and structure["labels"]:
            class_ids = set()
            for label_file in structure["labels"][:100]:
                try:
                    with open(label_file, 'r') as f:
                        for line in f:
                            parts = line.strip().split()
                            if parts:
                                class_ids.add(int(parts[0]))
                except:
                    continue
            classes = [f"class_{i}" for i in sorted(class_ids)]
            update_status(task_id, "packaging", 80, "从标签推断类别", f"类别: {classes}")

        # 创建 dataset.yaml
        yaml_content = f"""path: .
train: train/images
val: val/images
nc: {len(classes)}
names: {classes}
"""
        with open(os.path.join(dataset_dir, "dataset.yaml"), "w") as f:
            f.write(yaml_content)

        update_status(task_id, "packaging", 82, "创建 dataset.yaml", f"类别数: {len(classes)}")

        # 重新打包为 ZIP
        update_status(task_id, "packaging", 84, "重新打包数据集...", "")

        final_zip_path = os.path.join(temp_dir, "dataset_final.zip")
        with zipfile.ZipFile(final_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(dataset_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, dataset_dir)
                    zipf.write(file_path, arcname)

        update_status(task_id, "packaging", 85, "打包完成",
                      f"大小: {format_file_size(os.path.getsize(final_zip_path))}")

        # 阶段 5: 上传到 Storage (85-90%)
        update_status(task_id, "packaging", 86, "上传处理后的数据集...", "")

        dataset_id = f"{request.project_id}_local_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        final_storage_path = f"projects/{request.project_id}/datasets/{dataset_id}.zip"

        with open(final_zip_path, "rb") as f:
            supabase.storage.from_(request.bucket).upload(
                final_storage_path,
                f,
                file_options={"content-type": "application/zip"}
            )

        update_status(task_id, "packaging", 88, "上传完成", f"路径: {final_storage_path}")

        # 删除原始上传的 ZIP
        try:
            supabase.storage.from_(request.bucket).remove([request.storage_path])
            update_status(task_id, "packaging", 89, "清理临时文件", "")
        except:
            pass

        # 阶段 6: 保存到数据库 (90-100%)
        update_status(task_id, "saving", 90, "保存到数据库...", "")

        stats = {
            "train": len(train_images),
            "val": len(val_images),
            "total": len(all_images),
            "classes": len(classes),
            "class_names": classes
        }

        dataset_record = {
            "dataset_id": dataset_id,
            "project_id": request.project_id,
            "name": request.dataset_name,
            "description": f"从本地上传的 ZIP 数据集: {request.original_filename or 'unknown'}",
            "storage_path": final_storage_path,
            "bucket": request.bucket,
            "stats": stats,
            "source_tasks": [],
            "has_original_dataset": True,
            "status": "ready",
            "created_at": datetime.now().isoformat()
        }

        supabase.table("datasets").insert(dataset_record).execute()
        update_status(task_id, "saving", 95, "数据库记录创建成功", f"ID: {dataset_id}")

        # 更新全局状态
        dataset_registry[request.project_id] = {
            "dataset_id": dataset_id,
            "storage_path": final_storage_path,
            "local_path": dataset_dir,
            "stats": stats,
            "ready": True
        }

        update_status(task_id, "completed", 100, "处理完成！",
                      f"共 {stats['total']} 张图片, {stats['classes']} 个类别",
                      result={
                          "dataset_id": dataset_id,
                          "stats": stats,
                          "storage_path": final_storage_path
                      })

    except Exception as e:
        error_msg = str(e)
        print(f"[{task_id}] [ERROR] {error_msg}")
        import traceback
        print(traceback.format_exc())

        update_status(task_id, "error", 0, f"处理失败: {error_msg}", "")

        # 清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


# ===== API 路由 =====

@router.post("/upload-local", response_model=DatasetStatusResponse)
async def upload_local_dataset(
        project_id: Annotated[str, Form(..., description="项目ID")],
        dataset_name: Annotated[str, Form(..., description="数据集名称")],
        files: Annotated[List[UploadFile], File(..., description="数据集文件列表")],
):
    """
    接收前端上传的本地数据集文件，保存到 Storage（保留用于小文件上传）
    """
    print(f"[DEBUG] 收到上传请求: project_id={project_id}, dataset_name={dataset_name}")
    print(f"[DEBUG] files 数量: {len(files)}")

    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="Missing form field: files")

    temp_dir = None
    try:
        temp_dir = f"/tmp/local_upload_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        os.makedirs(temp_dir, exist_ok=True)

        # 保存上传的文件
        saved_files = []
        for file in files:
            original_filename = file.filename
            file_path = os.path.join(temp_dir, original_filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            saved_files.append(file_path)

        # 分析数据集结构
        structure = analyze_local_dataset(temp_dir)

        # 创建标准的 YOLO 结构
        dataset_dir = os.path.join(temp_dir, "dataset")
        os.makedirs(os.path.join(dataset_dir, "train", "images"), exist_ok=True)
        os.makedirs(os.path.join(dataset_dir, "train", "labels"), exist_ok=True)
        os.makedirs(os.path.join(dataset_dir, "val", "images"), exist_ok=True)
        os.makedirs(os.path.join(dataset_dir, "val", "labels"), exist_ok=True)

        # 分配训练集和验证集 (80/20)
        import random
        random.seed(42)
        all_images = structure["images"]
        random.shuffle(all_images)
        split_idx = int(len(all_images) * 0.8)
        train_images = all_images[:split_idx]
        val_images = all_images[split_idx:]

        def copy_split(images, split_name):
            for img_path in images:
                img_name = os.path.basename(img_path)
                label_name = os.path.splitext(img_name)[0] + ".txt"
                label_path = os.path.join(structure["labels_dir"], label_name)

                shutil.copy2(img_path, os.path.join(dataset_dir, split_name, "images", img_name))
                if os.path.exists(label_path):
                    shutil.copy2(label_path, os.path.join(dataset_dir, split_name, "labels", label_name))

        copy_split(train_images, "train")
        copy_split(val_images, "val")

        # 读取类别信息
        classes = []
        classes_file = os.path.join(structure["root_dir"], "classes.txt")
        if os.path.exists(classes_file):
            with open(classes_file, 'r') as f:
                classes = [line.strip() for line in f if line.strip()]

        if not classes and structure["labels"]:
            class_ids = set()
            for label_file in structure["labels"][:100]:
                with open(label_file, 'r') as f:
                    for line in f:
                        class_id = line.strip().split()[0]
                        class_ids.add(int(class_id))
            classes = [f"class_{i}" for i in sorted(class_ids)]

        # 创建 dataset.yaml
        yaml_content = f"""
path: .
train: train/images
val: val/images
nc: {len(classes)}
names: {classes}
"""
        with open(os.path.join(dataset_dir, "dataset.yaml"), "w") as f:
            f.write(yaml_content)

        # 打包为 ZIP
        zip_path = f"{temp_dir}/dataset.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(dataset_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, dataset_dir)
                    zipf.write(file_path, arcname)

        # 上传到 Supabase Storage
        from supabase import create_client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        supabase = create_client(supabase_url, supabase_key)

        bucket_name = "datasets"
        dataset_id = f"{project_id}_local_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        storage_path = f"projects/{project_id}/datasets/{dataset_id}.zip"

        with open(zip_path, "rb") as f:
            supabase.storage.from_(bucket_name).upload(
                storage_path,
                f,
                file_options={"content-type": "application/zip"}
            )

        # 统计信息
        stats = {
            "train": len(train_images),
            "val": len(val_images),
            "total": len(all_images),
            "classes": len(classes),
            "class_names": classes
        }

        # 保存到数据库
        dataset_record = {
            "dataset_id": dataset_id,
            "project_id": project_id,
            "name": dataset_name,
            "description": "从本地上传的数据集",
            "storage_path": storage_path,
            "bucket": bucket_name,
            "stats": stats,
            "source_tasks": [],
            "has_original_dataset": True,
            "status": "ready",
            "created_at": datetime.now().isoformat()
        }

        supabase.table("datasets").insert(dataset_record).execute()

        # 更新全局状态
        dataset_registry[project_id] = {
            "dataset_id": dataset_id,
            "storage_path": storage_path,
            "local_path": dataset_dir,
            "stats": stats,
            "ready": True
        }

        # 清理临时文件
        shutil.rmtree(temp_dir, ignore_errors=True)

        return DatasetStatusResponse(
            ready=True,
            message=f"本地数据集上传成功: {stats['total']} 张图片",
            dataset_id=dataset_id,
            stats=stats,
            storage_path=storage_path
        )

    except Exception as e:
        print(f"[ERROR] 上传失败: {str(e)}")
        import traceback
        print(traceback.format_exc())
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/process-from-storage", response_model=DatasetStatusResponse)
async def process_from_storage(
        request: ProcessFromStorageRequest,
        background_tasks: BackgroundTasks
):
    """
    从 Supabase Storage 下载 ZIP，解压处理，保存到数据库
    创建后台任务，立即返回任务ID
    """
    task_id = str(uuid.uuid4())

    # 初始化任务状态
    update_status(task_id, "pending", 0, "任务已创建", "等待处理...")

    # 后台处理
    background_tasks.add_task(process_dataset_task, task_id, request)

    # 立即返回任务ID，前端可以轮询状态
    return DatasetStatusResponse(
        ready=False,
        message="处理任务已创建",
        dataset_id=task_id,
        stats={"task_id": task_id, "status": "pending"}
    )


@router.get("/processing-status/{task_id}", response_model=ProcessingStatus)
async def get_processing_status(task_id: str):
    """
    获取处理任务状态
    """
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    return ProcessingStatus(**processing_tasks[task_id])


from datetime import datetime
from fastapi import APIRouter, HTTPException
import logging

logger = logging.getLogger(__name__)


@router.get("/status/{project_id}")
async def get_dataset_status(project_id: str, force_refresh: bool = False):
    """
    获取数据集状态
    参数:
        project_id: 项目ID
        force_refresh: 是否强制重新计算统计信息（默认False）
    """
    try:
        # 1. 先查数据库
        response = supabase.table("datasets") \
            .select("*") \
            .eq("project_id", project_id) \
            .eq("status", "ready") \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        if response.data:
            logger.info(f"数据库找到数据集记录 | project_id={project_id}")
            dataset = response.data[0]

            # 确保 stats 字段存在且格式正确
            stats = dataset.get('stats', {}) or {}

            # 判断是否需要重新计算
            should_recalculate = (
                    not stats or
                    stats.get('total', 0) == 0 or
                    force_refresh  # 强制刷新
            )

            if should_recalculate:
                reason = "force_refresh" if force_refresh else "empty/invalid"
                logger.warning(f"重新计算 stats | dataset_id={dataset.get('dataset_id')}, reason={reason}")

                stats = await recalculate_stats(
                    dataset['storage_path'],
                    dataset.get('bucket', 'datasets')
                )

                # 更新数据库（只有统计成功才更新）
                if stats['total'] > 0:
                    try:
                        supabase.table("datasets") \
                            .update({
                            "stats": stats,
                            "updated_at": datetime.now().isoformat()
                        }) \
                            .eq("dataset_id", dataset['dataset_id']) \
                            .execute()
                        logger.info(f"已更新数据库 stats | train={stats['train']}, val={stats['val']}")
                    except Exception as e:
                        logger.error(f"更新数据库 stats 失败: {e}")
                else:
                    logger.warning(f"重新计算后 stats 仍为 0，保留原值")
                    # 如果重新计算失败，保留原来的 stats（如果有）
                    if dataset.get('stats') and dataset['stats'].get('total', 0) > 0:
                        stats = dataset['stats']

            # 返回包含正确 stats 的数据
            return {
                "status": "ready",
                "dataset": {**dataset, "stats": stats},
                "source": "database",
                "refreshed": should_recalculate  # 告诉前端是否刚刷新过
            }

        # 2. 数据库无记录，扫描 Storage
        logger.warning(f"数据库无记录，尝试扫描 Storage | project_id={project_id}")

        # 列出 datasets bucket 根目录内容
        try:
            storage_response = supabase.storage \
                .from_("datasets") \
                .list("")
        except Exception as e:
            logger.error(f"无法访问 Storage: {e}")
            return {
                "status": "error",
                "message": f"无法访问 Storage: {str(e)}"
            }

        if not storage_response:
            return {
                "status": "empty",
                "message": "Storage 中未找到数据集"
            }

        # 3. 解析 Storage 内容，寻找有效数据集文件夹
        datasets_found = []
        for item in storage_response:
            if not item.get("id"):  # 跳过文件，只处理文件夹
                continue

            folder_name = item["name"]

            try:
                files = supabase.storage \
                    .from_("datasets") \
                    .list(folder_name)

                file_names = [f["name"] for f in files]

                # 检查是否包含数据集标识文件
                has_yaml = "data.yaml" in file_names or "dataset.yaml" in file_names
                has_classes = "classes.txt" in file_names
                has_train = "train" in file_names
                has_val = "val" in file_names

                if has_yaml or has_classes or (has_train and has_val):
                    datasets_found.append({
                        "name": folder_name,
                        "path": f"datasets/{folder_name}",
                        "files": file_names,
                        "has_structure": has_train and has_val
                    })
            except Exception as e:
                logger.debug(f"扫描文件夹 {folder_name} 失败: {e}")
                continue

        # 4. 自动同步到数据库
        synced_datasets = []
        for ds in datasets_found:
            try:
                # 读取 classes.txt 获取类别
                classes = []
                try:
                    file_response = supabase.storage \
                        .from_("datasets") \
                        .download(f"{ds['name']}/classes.txt")
                    if file_response:
                        content = file_response.decode('utf-8') if isinstance(file_response, bytes) else file_response
                        classes = [c.strip() for c in content.split('\n') if c.strip()]
                except Exception as e:
                    logger.debug(f"读取 classes.txt 失败: {e}")

                # 读取 data.yaml 获取格式信息
                data_format = "yolo"
                try:
                    yaml_response = supabase.storage \
                        .from_("datasets") \
                        .download(f"{ds['name']}/data.yaml")
                    if yaml_response:
                        content = yaml_response.decode('utf-8') if isinstance(yaml_response, bytes) else yaml_response
                        if 'train' in content and 'val' in content:
                            data_format = "yolo"
                except Exception as e:
                    logger.debug(f"读取 data.yaml 失败: {e}")

                # 尝试获取 stats（如果是文件夹结构）
                stats = {}
                if ds.get('has_structure'):
                    stats = await recalculate_stats(f"{ds['name']}", "datasets")

                # 插入数据库记录
                dataset_record = {
                    "dataset_id": f"dataset_{ds['name']}_{int(datetime.now().timestamp())}",
                    "project_id": project_id,
                    "name": ds["name"],
                    "description": f"从 Storage 自动同步的数据集",
                    "status": "ready",
                    "storage_path": ds["name"],  # 直接使用文件夹名
                    "bucket": "datasets",
                    "format": data_format,
                    "classes": classes,
                    "stats": stats,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }

                insert_response = supabase.table("datasets") \
                    .insert(dataset_record) \
                    .execute()

                if insert_response.data:
                    synced_datasets.append(dataset_record)
                    logger.info(f"成功同步数据集到数据库: {ds['name']} | stats={stats}")

            except Exception as e:
                logger.error(f"同步数据集 {ds['name']} 失败: {e}")
                continue

        # 5. 返回结果
        if synced_datasets:
            return {
                "status": "ready",
                "dataset": synced_datasets[0],
                "datasets": synced_datasets,
                "source": "storage_sync",
                "message": f"从 Storage 同步了 {len(synced_datasets)} 个数据集"
            }
        else:
            return {
                "status": "empty",
                "message": "Storage 中未找到有效数据集（需要包含 data.yaml、classes.txt 或 train/val 文件夹）"
            }

    except Exception as e:
        logger.error(f"获取数据集状态失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

async def scan_storage_and_sync(project_id: str, supabase_client) -> DatasetStatusResponse:
    """
    扫描 Storage 并同步数据集到数据库
    """
    try:
        bucket_name = "datasets"
        prefix = f"projects/{project_id}/"

        # 列出 Storage 中的文件
        files_result = supabase_client.storage.from_(bucket_name).list(prefix)

        if not files_result:
            return DatasetStatusResponse(
                ready=False,
                message="Storage 中没有找到数据集文件"
            )

        # 查找 ZIP 文件
        zip_files = [f for f in files_result if f.get("name", "").endswith(".zip")]

        if not zip_files:
            return DatasetStatusResponse(
                ready=False,
                message="没有找到 ZIP 格式的数据集文件"
            )

        # 处理最新的 ZIP 文件
        latest_zip = zip_files[-1]
        zip_name = latest_zip["name"]
        storage_path = f"{prefix}{zip_name}"

        # 下载并解析 ZIP
        zip_data = supabase_client.storage.from_(bucket_name).download(storage_path)

        # 解压分析
        temp_dir = f"/tmp/scan_{project_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        os.makedirs(temp_dir, exist_ok=True)

        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # 查找数据集根目录
        dataset_root = find_dataset_root(temp_dir)

        if not dataset_root:
            return DatasetStatusResponse(
                ready=False,
                message="ZIP 文件中未找到有效的数据集结构（需要包含 images/ 和 labels/）"
            )

        # 统计图片数量
        train_dir = os.path.join(dataset_root, "train", "images")
        val_dir = os.path.join(dataset_root, "val", "images")

        train_images = len([f for f in os.listdir(train_dir)
                            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))]) if os.path.exists(
            train_dir) else 0
        val_images = len([f for f in os.listdir(val_dir)
                          if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))]) if os.path.exists(
            val_dir) else 0

        # 读取类别信息
        classes = []
        classes_file = os.path.join(dataset_root, "classes.txt")
        if os.path.exists(classes_file):
            with open(classes_file, 'r') as f:
                classes = [line.strip() for line in f if line.strip()]

        if not classes:
            # 从 labels 推断
            labels_dir = os.path.join(dataset_root, "train", "labels")
            if os.path.exists(labels_dir):
                class_ids = set()
                for label_file in os.listdir(labels_dir)[:100]:
                    if label_file.endswith('.txt'):
                        with open(os.path.join(labels_dir, label_file), 'r') as f:
                            for line in f:
                                parts = line.strip().split()
                                if parts:
                                    class_ids.add(int(parts[0]))
                classes = [f"class_{i}" for i in sorted(class_ids)]

        stats = {
            "train": train_images,
            "val": val_images,
            "total": train_images + val_images,
            "classes": len(classes),
            "class_names": classes
        }

        # 生成 dataset_id
        dataset_id = f"{project_id}_auto_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 保存到数据库
        dataset_record = {
            "dataset_id": dataset_id,
            "project_id": project_id,
            "name": f"自动同步_{zip_name}",
            "description": f"从 Storage 自动扫描同步: {zip_name}",
            "storage_path": storage_path,
            "bucket": bucket_name,
            "stats": stats,
            "source_tasks": [],
            "has_original_dataset": True,
            "status": "ready",
            "created_at": datetime.now().isoformat()
        }

        supabase_client.table("datasets").insert(dataset_record).execute()
        logger.info(f"数据集已自动同步到数据库: {dataset_id}")

        # 更新内存 registry
        dataset_registry[project_id] = {
            "dataset_id": dataset_id,
            "storage_path": storage_path,
            "local_path": dataset_root,
            "stats": stats,
            "ready": True
        }

        # 清理临时文件
        shutil.rmtree(temp_dir, ignore_errors=True)

        return DatasetStatusResponse(
            ready=True,
            message=f"数据集已自动同步: {stats['total']} 张图片, {stats['classes']} 个类别",
            dataset_id=dataset_id,
            stats=stats,
            storage_path=storage_path,
            created_at=dataset_record["created_at"]
        )

    except Exception as e:
        logger.error(f"扫描 Storage 失败: {str(e)}")
        return DatasetStatusResponse(
            ready=False,
            message=f"自动同步失败: {str(e)}"
        )


@router.get("/status/default")
async def get_default_dataset_status():
    """默认数据集状态检查"""
    dataset_dir = Path("./datasets/custom")
    train_images = dataset_dir / "train" / "images"
    val_images = dataset_dir / "val" / "images"

    if train_images.exists() and val_images.exists():
        train_count = len(list(train_images.glob("*")))
        val_count = len(list(val_images.glob("*")))

        if train_count > 0:
            return {
                "ready": True,
                "message": f"本地数据集已就绪: {train_count} 张训练图片, {val_count} 张验证图片",
                "stats": {"train": train_count, "val": val_count}
            }

    return {
        "ready": False,
        "message": "数据集未准备，请先完成标注并合并数据集，或上传本地数据集"
    }


@router.post("/download-for-training/{project_id}")
async def download_dataset_for_training(project_id: str):
    """
    下载数据集到本地，准备训练
    """
    if project_id not in dataset_registry:
        raise HTTPException(status_code=404, detail="数据集未找到")

    info = dataset_registry[project_id]
    local_path = f"/app/datasets/{project_id}_{info['dataset_id']}"

    if os.path.exists(local_path) and os.path.exists(os.path.join(local_path, "dataset.yaml")):
        return {
            "success": True,
            "path": local_path,
            "stats": info["stats"]
        }

    try:
        from supabase import create_client
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

        os.makedirs(local_path, exist_ok=True)
        zip_data = supabase.storage.from_("datasets").download(info["storage_path"])

        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_ref:
            zip_ref.extractall(local_path)

        dataset_registry[project_id]["local_path"] = local_path

        return {
            "success": True,
            "path": local_path,
            "stats": info["stats"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


# ===== 保留的路由（上传标注、合并数据集）=====

@router.post("/upload-annotations", response_model=DatasetStatusResponse)
async def upload_annotations(
        data: AnnotationData,
        background_tasks: BackgroundTasks
):
    """
    上传标注结果到 Storage，并创建YOLO格式数据集
    """
    try:
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        supabase = create_client(supabase_url, supabase_key)

        # 1. 创建临时目录处理数据
        temp_dir = f"/tmp/dataset_{data.task_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        os.makedirs(temp_dir, exist_ok=True)

        images_dir = os.path.join(temp_dir, "images")
        labels_dir = os.path.join(temp_dir, "labels")
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(labels_dir, exist_ok=True)

        # 2. 下载图片
        import requests
        img_response = requests.get(data.image_url, timeout=30)
        if img_response.status_code != 200:
            raise HTTPException(status_code=400, detail="无法下载图片")

        # 获取图片尺寸
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(img_response.content))
        img_width, img_height = img.size

        # 保存图片
        img_ext = os.path.splitext(data.image_url)[1] or ".jpg"
        img_name = f"{data.task_id}{img_ext}"
        img_path = os.path.join(images_dir, img_name)
        img.save(img_path)

        # 3. 转换标注为YOLO格式
        label_name = os.path.splitext(img_name)[0] + ".txt"
        label_path = os.path.join(labels_dir, label_name)

        # 创建类别映射
        class_map = {name: idx for idx, name in enumerate(data.label_map.keys())}

        yolo_lines = []
        for ann in data.annotations:
            class_id = class_map.get(ann["label"], 0)
            # 转换为YOLO格式 (x_center, y_center, width, height) - 归一化
            x_center = (ann["x"] + ann["width"] / 2) / img_width
            y_center = (ann["y"] + ann["height"] / 2) / img_height
            norm_width = ann["width"] / img_width
            norm_height = ann["height"] / img_height

            # 确保值在0-1范围内
            x_center = max(0, min(1, x_center))
            y_center = max(0, min(1, y_center))
            norm_width = max(0, min(1, norm_width))
            norm_height = max(0, min(1, norm_height))

            yolo_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {norm_width:.6f} {norm_height:.6f}")

        with open(label_path, "w") as f:
            f.write("\n".join(yolo_lines))

        # 4. 创建 dataset.yaml
        yaml_content = f"""
path: .
train: images
val: images
nc: {len(class_map)}
names: {list(class_map.keys())}
"""
        with open(os.path.join(temp_dir, "dataset.yaml"), "w") as f:
            f.write(yaml_content)

        # 5. 创建 classes.txt
        with open(os.path.join(temp_dir, "classes.txt"), "w") as f:
            for name, idx in sorted(class_map.items(), key=lambda x: x[1]):
                f.write(f"{idx} {name}\n")

        # 6. 打包为zip
        zip_path = f"{temp_dir}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)

        # 7. 上传到 Supabase Storage
        bucket_name = "datasets"
        safe_task_segment = _safe_storage_segment(data.task_id, "task")
        storage_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S_%f')}_{uuid.uuid4().hex[:8]}.zip"
        storage_path = f"annotations/{safe_task_segment}/{storage_filename}"

        # 确保bucket存在
        try:
            supabase.storage.get_bucket(bucket_name)
        except:
            supabase.storage.create_bucket(bucket_name, options={"public": False})

        with open(zip_path, "rb") as f:
            upload_result = supabase.storage.from_(bucket_name).upload(
                storage_path,
                f,
                file_options={"content-type": "application/zip", "upsert": "true"}
            )

        # 8. 保存元数据到数据库
        metadata = {
            "task_id": data.task_id,
            "image_url": data.image_url,
            "storage_path": storage_path,
            "bucket": bucket_name,
            "annotations_count": len(data.annotations),
            "labels": list(data.label_map.keys()),
            "image_size": {"width": img_width, "height": img_height},
            "created_at": datetime.now().isoformat(),
            "format": "yolo"
        }

        # 保存到 annotation_exports 表，避免与标注框明细表混用
        supabase.table(ANNOTATION_EXPORTS_TABLE).insert(metadata).execute()

        # 9. 清理临时文件
        shutil.rmtree(temp_dir, ignore_errors=True)
        if os.path.exists(zip_path):
            os.remove(zip_path)

        return DatasetStatusResponse(
            ready=True,
            message=f"标注数据已上传: {len(data.annotations)} 个标注",
            storage_path=storage_path,
            stats={"annotations": len(data.annotations), "labels": len(class_map)}
        )

    except Exception as e:
        # 清理临时文件
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/merge-and-prepare", response_model=DatasetStatusResponse)
async def merge_and_prepare_dataset(request: DatasetMergeRequest):
    """
    合并多个标注任务的数据集，并可选择合并原始数据集
    """
    try:
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        supabase = create_client(supabase_url, supabase_key)

        bucket_name = "datasets"
        dataset_id = f"{request.project_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        temp_dir = f"/tmp/merge_{dataset_id}"

        # 创建目录结构
        train_images = os.path.join(temp_dir, "train", "images")
        train_labels = os.path.join(temp_dir, "train", "labels")
        val_images = os.path.join(temp_dir, "val", "images")
        val_labels = os.path.join(temp_dir, "val", "labels")

        for d in [train_images, train_labels, val_images, val_labels]:
            os.makedirs(d, exist_ok=True)

        all_labels = set()
        annotation_records = []

        # 1. 下载所有标注数据
        for task_id in request.annotation_tasks:
            # 从数据库获取标注元数据
            result = supabase.table(ANNOTATION_EXPORTS_TABLE).select("*").eq("task_id", task_id).execute()

            if not result.data:
                continue

            record = result.data[0]
            annotation_records.append(record)

            # 下载zip文件
            storage_path = record["storage_path"]
            try:
                zip_data = supabase.storage.from_(bucket_name).download(storage_path)

                # 解压到临时目录
                import zipfile
                import io
                with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_ref:
                    zip_ref.extractall(os.path.join(temp_dir, f"task_{task_id}"))

                # 收集所有标签
                all_labels.update(record.get("labels", []))
            except Exception as e:
                print(f"下载任务 {task_id} 失败: {e}")
                continue

        # 2. 合并数据（80%训练，20%验证）
        import random
        random.seed(42)

        all_images = []
        for root, dirs, files in os.walk(temp_dir):
            if "images" in root and "task_" in root:
                for f in files:
                    if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                        all_images.append(os.path.join(root, f))

        random.shuffle(all_images)
        split_idx = int(len(all_images) * 0.8)
        train_files = all_images[:split_idx]
        val_files = all_images[split_idx:]

        # 复制文件到目标目录
        def copy_files(files, target_img_dir, target_lbl_dir):
            for img_path in files:
                task_dir = os.path.dirname(os.path.dirname(img_path))
                lbl_path = os.path.join(task_dir, "labels",
                                        os.path.splitext(os.path.basename(img_path))[0] + ".txt")

                # 复制图片
                shutil.copy2(img_path, os.path.join(target_img_dir, os.path.basename(img_path)))
                # 复制标签
                if os.path.exists(lbl_path):
                    shutil.copy2(lbl_path, os.path.join(target_lbl_dir, os.path.basename(lbl_path)))

        copy_files(train_files, train_images, train_labels)
        copy_files(val_files, val_images, val_labels)

        # 3. 可选：合并原始数据集
        if request.original_dataset_path and os.path.exists(request.original_dataset_path):
            # 假设原始数据集也是YOLO格式
            orig_train_img = os.path.join(request.original_dataset_path, "train", "images")
            orig_train_lbl = os.path.join(request.original_dataset_path, "train", "labels")
            orig_val_img = os.path.join(request.original_dataset_path, "val", "images")
            orig_val_lbl = os.path.join(request.original_dataset_path, "val", "labels")

            # 复制原始数据（保持比例）
            if os.path.exists(orig_train_img):
                for f in os.listdir(orig_train_img):
                    if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                        shutil.copy2(os.path.join(orig_train_img, f), train_images)
                        lbl = os.path.splitext(f)[0] + ".txt"
                        if os.path.exists(os.path.join(orig_train_lbl, lbl)):
                            shutil.copy2(os.path.join(orig_train_lbl, lbl), train_labels)
                            # 读取标签类别
                            with open(os.path.join(orig_train_lbl, lbl), 'r') as lf:
                                for line in lf:
                                    parts = line.strip().split()
                                    if parts:
                                        all_labels.add(f"class_{parts[0]}")  # 简化处理

        # 4. 创建最终的 dataset.yaml
        class_list = sorted(list(all_labels))
        class_map = {name: idx for idx, name in enumerate(class_list)}

        yaml_content = f"""
path: .
train: train/images
val: val/images
nc: {len(class_list)}
names: {class_list}
"""
        with open(os.path.join(temp_dir, "dataset.yaml"), "w") as f:
            f.write(yaml_content)

        # 5. 创建统计信息
        train_count = len(os.listdir(train_images))
        val_count = len(os.listdir(val_images))

        stats = {
            "train": train_count,
            "val": val_count,
            "total": train_count + val_count,
            "classes": len(class_list),
            "class_names": class_list
        }

        # 6. 打包并上传
        final_zip = f"{temp_dir}.zip"
        with zipfile.ZipFile(final_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)

        # 上传到 Storage
        final_storage_path = f"projects/{request.project_id}/datasets/{dataset_id}.zip"

        with open(final_zip, "rb") as f:
            supabase.storage.from_(bucket_name).upload(
                final_storage_path,
                f,
                file_options={"content-type": "application/zip"}
            )

        # 7. 保存数据集记录到数据库
        dataset_record = {
            "dataset_id": dataset_id,
            "project_id": request.project_id,
            "name": request.dataset_name,
            "description": request.description,
            "storage_path": final_storage_path,
            "bucket": bucket_name,
            "stats": stats,
            "source_tasks": request.annotation_tasks,
            "has_original_dataset": request.original_dataset_path is not None,
            "status": "ready",
            "created_at": datetime.now().isoformat()
        }

        supabase.table("datasets").insert(dataset_record).execute()

        # 8. 更新全局数据集状态（用于训练页面检查）
        dataset_registry[request.project_id] = {
            "dataset_id": dataset_id,
            "storage_path": final_storage_path,
            "local_path": temp_dir,
            "stats": stats,
            "ready": True
        }

        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)
        if os.path.exists(final_zip):
            os.remove(final_zip)

        return DatasetStatusResponse(
            ready=True,
            message=f"数据集准备完成: {stats['total']} 张图片, {stats['classes']} 个类别",
            dataset_id=dataset_id,
            stats=stats,
            storage_path=final_storage_path,
            created_at=datetime.now().isoformat()
        )

    except Exception as e:
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"合并失败: {str(e)}")


# ===== 在 dataset_routes.py 文件末尾添加以下内容 =====

import asyncio
from fastapi import WebSocket
from app.core.ws_manager import progress_ws_manager

# 独立缓存目录
CACHE_DIR = Path("./cache/datasets")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class DatasetCacheManager:
    """数据集缓存管理器：负责临时下载和清理"""

    def __init__(self):
        self.cache_dir = CACHE_DIR
        self.active_downloads: Dict[str, dict] = {}  # 跟踪下载进度

    def get_cache_path(self, dataset_id: str) -> Path:
        """获取缓存路径"""
        return self.cache_dir / dataset_id

    def is_cached(self, dataset_id: str) -> bool:
        """检查是否已缓存"""
        cache_path = self.get_cache_path(dataset_id)
        yaml_file = cache_path / "data.yaml"
        return cache_path.exists() and yaml_file.exists()

    async def download_with_progress(
            self,
            dataset_id: str,
            storage_path: str,
            bucket: str = "datasets",
            username: str = None
    ) -> Path:
        """
        带进度跟踪的下载
        """
        cache_path = self.get_cache_path(dataset_id)
        cache_path.mkdir(parents=True, exist_ok=True)

        self.active_downloads[dataset_id] = {
            "status": "downloading",
            "percent": 0,
            "message": "开始下载...",
            "detail": ""
        }

        try:
            supabase_client = get_supabase_client()

            # 1. 获取文件信息
            self.active_downloads[dataset_id]["message"] = "获取文件信息..."
            self.active_downloads[dataset_id]["percent"] = 5

            # 2. 下载 ZIP 到临时文件
            temp_zip = cache_path / "dataset.zip"
            self.active_downloads[dataset_id]["message"] = "下载数据集文件..."
            self.active_downloads[dataset_id]["percent"] = 10

            # 使用流式下载
            response = supabase_client.storage.from_(bucket).download(storage_path)

            if isinstance(response, bytes):
                total_size = len(response)
                # 模拟进度（因为 Supabase Python 客户端不支持流式进度回调）
                chunk_size = max(1, total_size // 10)
                downloaded = 0

                with open(temp_zip, "wb") as f:
                    for i in range(0, total_size, chunk_size):
                        chunk = response[i:i + chunk_size]
                        f.write(chunk)
                        downloaded += len(chunk)
                        percent = 10 + int((downloaded / total_size) * 40)  # 10-50%
                        self.active_downloads[dataset_id]["percent"] = percent
                        self.active_downloads[dataset_id][
                            "detail"] = f"{format_file_size(downloaded)} / {format_file_size(total_size)}"

                        # 发送 WebSocket 进度
                        if username:
                            await progress_ws_manager.emit_to_users(
                                [username],
                                {
                                    "type": "DATASET_DOWNLOAD_PROGRESS",
                                    "dataset_id": dataset_id,
                                    "percent": percent,
                                    "message": self.active_downloads[dataset_id]["message"],
                                    "detail": self.active_downloads[dataset_id]["detail"]
                                }
                            )
                        await asyncio.sleep(0.05)  # 模拟网络延迟，让前端看到动画

            # 3. 解压
            self.active_downloads[dataset_id]["message"] = "解压数据集..."
            self.active_downloads[dataset_id]["percent"] = 55

            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(cache_path)

            # 4. 查找数据集根目录
            self.active_downloads[dataset_id]["message"] = "查找数据集结构..."
            self.active_downloads[dataset_id]["percent"] = 70

            dataset_root = find_dataset_root(str(cache_path))
            if dataset_root and dataset_root != str(cache_path):
                # 如果解压到了子目录，移动文件到根目录
                for item in os.listdir(dataset_root):
                    shutil.move(os.path.join(dataset_root, item), str(cache_path))

            # 5. 验证结构
            self.active_downloads[dataset_id]["message"] = "验证数据集结构..."
            self.active_downloads[dataset_id]["percent"] = 85

            train_images = cache_path / "train" / "images"
            val_images = cache_path / "val" / "images"

            if not train_images.exists() or not val_images.exists():
                raise Exception("数据集结构不完整，缺少 train/images 或 val/images")

            # 6. 生成 data.yaml
            self.active_downloads[dataset_id]["message"] = "生成配置文件..."
            self.active_downloads[dataset_id]["percent"] = 95

            classes_file = cache_path / "classes.txt"
            if classes_file.exists():
                with open(classes_file, 'r') as f:
                    names = [l.strip() for l in f if l.strip()]
            else:
                # 从 labels 推断
                labels_dir = cache_path / "train" / "labels"
                class_ids = set()
                if labels_dir.exists():
                    for f in labels_dir.glob("*.txt"):
                        with open(f) as file:
                            for line in file:
                                parts = line.strip().split()
                                if parts:
                                    class_ids.add(int(parts[0]))
                names = [f"class_{i}" for i in sorted(class_ids)] if class_ids else ["object"]

            yaml_content = f"""path: {cache_path.absolute()}
train: train/images
val: val/images
nc: {len(names)}
names: {names}
"""
            yaml_path = cache_path / "data.yaml"
            with open(yaml_path, "w") as f:
                f.write(yaml_content)

            # 7. 清理 ZIP 文件
            if temp_zip.exists():
                temp_zip.unlink()

            self.active_downloads[dataset_id]["status"] = "completed"
            self.active_downloads[dataset_id]["percent"] = 100
            self.active_downloads[dataset_id]["message"] = "下载完成"

            # 发送完成通知
            if username:
                await progress_ws_manager.emit_to_users(
                    [username],
                    {
                        "type": "DATASET_DOWNLOAD_PROGRESS",
                        "dataset_id": dataset_id,
                        "percent": 100,
                        "message": "下载完成",
                        "detail": f"缓存路径: {cache_path}",
                        "status": "completed"
                    }
                )

            return cache_path

        except Exception as e:
            self.active_downloads[dataset_id]["status"] = "error"
            self.active_downloads[dataset_id]["message"] = f"下载失败: {str(e)}"

            # 清理失败的缓存
            if cache_path.exists():
                shutil.rmtree(cache_path, ignore_errors=True)

            if username:
                await progress_ws_manager.emit_to_users(
                    [username],
                    {
                        "type": "DATASET_DOWNLOAD_PROGRESS",
                        "dataset_id": dataset_id,
                        "percent": 0,
                        "message": "下载失败",
                        "detail": str(e),
                        "status": "error"
                    }
                )

            raise

    def get_progress(self, dataset_id: str) -> dict:
        """获取下载进度"""
        return self.active_downloads.get(dataset_id, {
            "status": "unknown",
            "percent": 0,
            "message": "未开始下载"
        })

    def cleanup(self, dataset_id: str = None):
        """清理缓存"""
        if dataset_id:
            cache_path = self.get_cache_path(dataset_id)
            if cache_path.exists():
                shutil.rmtree(cache_path, ignore_errors=True)
            self.active_downloads.pop(dataset_id, None)
        else:
            # 清理所有缓存（谨慎使用）
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir, ignore_errors=True)
                self.cache_dir.mkdir(parents=True, exist_ok=True)


# 全局缓存管理器
dataset_cache_manager = DatasetCacheManager()


# ===== 新 API 路由 =====

@router.get("/cache-status/{dataset_id}")
async def get_cache_status(dataset_id: str):
    """获取数据集缓存状态"""
    is_cached = dataset_cache_manager.is_cached(dataset_id)
    progress = dataset_cache_manager.get_progress(dataset_id)

    return {
        "dataset_id": dataset_id,
        "cached": is_cached,
        "cache_path": str(dataset_cache_manager.get_cache_path(dataset_id)) if is_cached else None,
        "progress": progress
    }


@router.post("/prepare-for-training/{project_id}")
async def prepare_dataset_for_training(
        project_id: str,
        background_tasks: BackgroundTasks,
        authorization: str = Header(default=None)
):
    """
    准备训练：临时下载数据集到缓存目录
    前端点击"开始训练"时调用
    """
    try:
        # 1. 获取当前用户
        from app.core.auth_utils import _resolve_user_id_from_token
        from app.db.session import SessionLocal
        from app.models import User

        username = None
        if authorization:
            user_id = _resolve_user_id_from_token(authorization)
            if user_id:
                db = SessionLocal()
                try:
                    user = db.query(User).filter(User.id == user_id).first()
                    if user:
                        username = user.username
                finally:
                    db.close()

        # 2. 查询数据集信息（只查元数据，不下载）
        response = supabase.table("datasets") \
            .select("*") \
            .eq("project_id", project_id) \
            .eq("status", "ready") \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        if not response.data:
            raise HTTPException(404, detail="未找到就绪的数据集")

        dataset = response.data[0]
        dataset_id = dataset["dataset_id"]
        storage_path = dataset["storage_path"]
        bucket = dataset.get("bucket", "datasets")

        # 3. 检查是否已缓存
        if dataset_cache_manager.is_cached(dataset_id):
            cache_path = dataset_cache_manager.get_cache_path(dataset_id)
            return {
                "success": True,
                "dataset_id": dataset_id,
                "cached": True,
                "cache_path": str(cache_path),
                "message": "数据集已缓存，可直接开始训练"
            }

        # 4. 开始下载（后台任务）
        async def download_task():
            try:
                await dataset_cache_manager.download_with_progress(
                    dataset_id=dataset_id,
                    storage_path=storage_path,
                    bucket=bucket,
                    username=username
                )
            except Exception as e:
                logger.error(f"数据集下载失败: {e}")

        # 立即启动下载
        asyncio.create_task(download_task())

        return {
            "success": True,
            "dataset_id": dataset_id,
            "cached": False,
            "message": "开始下载数据集到缓存...",
            "progress": dataset_cache_manager.get_progress(dataset_id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"准备训练失败: {e}")
        raise HTTPException(500, detail=str(e))


@router.post("/cleanup-cache/{dataset_id}")
async def cleanup_dataset_cache(dataset_id: str):
    """清理数据集缓存"""
    dataset_cache_manager.cleanup(dataset_id)
    return {
        "success": True,
        "message": f"已清理数据集 {dataset_id} 的缓存"
    }


@router.get("/download-progress/{dataset_id}")
async def get_download_progress(dataset_id: str):
    """获取下载进度（轮询用）"""
    return dataset_cache_manager.get_progress(dataset_id)