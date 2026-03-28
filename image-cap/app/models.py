# backend/app/models.py
import uuid
from uuid import UUID

from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, Boolean, JSON
from datetime import datetime
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    username = Column(String, unique=True)
    role = Column(String)  # annotator, reviewer, admin


class Project(Base):
    """项目表"""
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联关系
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")


class ProjectFile(Base):
    """项目文件表"""
    __tablename__ = "project_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    uploaded_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="pending")  # ✅ pending, labeling, done

    # 关联关系
    project = relationship("Project", back_populates="files")


class Review(Base):
    """审核表"""
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id"))
    reviewer_id = Column(String)
    status = Column(String)  # approved, rejected
    comments = Column(Text)


class Task(Base):
    """任务表"""
    __tablename__ = "tasks"
    id = Column(String, primary_key=True)
    image_url = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, annotating, completed, reviewed
    assigned_to = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    annotations_count = Column(Integer, default=0)


class Annotation(Base):
    """标注结果表"""
    __tablename__ = "annotations"
    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id"))
    label = Column(String, nullable=False)
    x = Column(Float)
    y = Column(Float)
    width = Column(Float)
    height = Column(Float)
    confidence = Column(Float, default=1.0)
    color = Column(String, default='#0000ff')
    annotated_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Draft(Base):
    """草稿表"""
    __tablename__ = "drafts"
    task_id = Column(String, primary_key=True)
    user_id = Column(String)
    annotations_json = Column(Text)
    saved_at = Column(DateTime, default=datetime.utcnow)


# 新增：增强的模型版本表
class ModelVersion(Base):
    """模型版本表（增强版，用于跟踪训练效果）"""
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True)
    version_name = Column(String, nullable=False)
    training_data_count = Column(Integer, default=0)

    # 详细评估指标
    map50 = Column(Float, default=0.0)  # mAP@0.5
    map75 = Column(Float, default=0.0)  # mAP@0.75
    map50_95 = Column(Float, default=0.0)  # mAP@0.5:0.95（COCO标准）
    precision = Column(Float, default=0.0)
    recall = Column(Float, default=0.0)
    fitness = Column(Float, default=0.0)  # 综合适应度分数

    # 损失值
    val_box_loss = Column(Float, default=0.0)
    val_cls_loss = Column(Float, default=0.0)
    val_dfl_loss = Column(Float, default=0.0)

    # 训练配置
    epochs_trained = Column(Integer, default=0)
    epochs_total = Column(Integer, default=0)
    batch_size = Column(Integer, default=16)
    model_size = Column(String, default='n')  # n, s, m, l, x
    hyperparameters = Column(JSON, default=dict)  # 存储完整训练配置

    # 路径和状态
    model_path = Column(String)
    local_path = Column(String)
    is_active = Column(Boolean, default=False)
    training_status = Column(String, default='pending')  # pending, running, completed, failed

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    training_duration_minutes = Column(Float, default=0.0)

    # 数据集信息
    dataset_info = Column(JSON, default=dict)


# 修改 models.py 中的 User 模型，并新增组织和邀请模型
class User(Base):
    """用户表"""
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    username = Column(String, unique=True)
    password_hash = Column(String, nullable=False)  # 新增
    avatar_url = Column(String, nullable=True)  # 新增
    is_active = Column(Boolean, default=True)  # 新增
    role = Column(String, default="annotator")
    created_at = Column(DateTime, default=datetime.utcnow)  # 新增
    last_login_at = Column(DateTime, nullable=True)  # 新增

    # 新增关联
    organizations = relationship("UserOrganization", back_populates="user")


# --- 以下为 models.py 需新增的模型 ---

class Organization(Base):
    """团队/组织表"""
    __tablename__ = "organizations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nickname = Column(String, nullable=False)
    org_type = Column(String, default="团队")  # 个人 或 团队
    member_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    members = relationship("UserOrganization", back_populates="organization")


class UserOrganization(Base):
    """用户与团队多对多关联表"""
    __tablename__ = "user_organizations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    organization_id = Column(String, ForeignKey("organizations.id"))
    joined_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="organizations")
    organization = relationship("Organization", back_populates="members")


class TeamInvitation(Base):
    """团队邀请表"""
    __tablename__ = "team_invitations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    token = Column(String, unique=True, nullable=False)
    organization_id = Column(String, ForeignKey("organizations.id"))
    inviter_id = Column(String, ForeignKey("users.id"))
    accepted_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)

    organization = relationship("Organization")
    inviter = relationship("User", foreign_keys=[inviter_id])
# 新增：训练任务队列表
class TrainingJob(Base):
    """训练任务队列表"""
    __tablename__ = "training_jobs"

    id = Column(Integer, primary_key=True)
    job_type = Column(String, default='standard')  # standard, hyperparameter_tuning, fine_tune
    status = Column(String, default='queued')  # queued, running, completed, failed, cancelled
    priority = Column(Integer, default=0)  # 优先级，数字越大越优先

    # 配置
    config = Column(JSON, default=dict)  # 训练配置
    dataset_path = Column(String)

    # 进度
    progress_percent = Column(Integer, default=0)
    current_epoch = Column(Integer, default=0)
    total_epochs = Column(Integer, default=0)
    current_metrics = Column(JSON, default=dict)  # 实时指标

    # 结果
    result_model_id = Column(Integer, ForeignKey("model_versions.id"), nullable=True)
    error_message = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # 创建者
    created_by = Column(String, default='system')
    # 调试：打印 ProjectFile 的所有列
    print("=" * 50)
    print("ProjectFile 列:", ProjectFile.__table__.columns.keys())
    print("=" * 50)