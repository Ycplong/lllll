from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from flask_migrate import Migrate

db = SQLAlchemy()

# 创建Flask应用
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdatabase.db'  # 替换为你的数据库 URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 创建数据库实例
db = SQLAlchemy(app)

# 创建迁移实例
migrate = Migrate(app, db)

class Machine(db.Model):
    """Machine Model"""
    __tablename__ = 'machine'

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String(50), unique=True, nullable=False)
    product_id = db.Column(db.String(50), nullable=False)
    step_id = db.Column(db.String(50), nullable=False)
    recipe_id = db.Column(db.String(50), nullable=False)
    review_id = db.Column(db.String(50), nullable=False)
    review_tool = db.Column(db.String(50), nullable=False)  # 评审工具
    inspection_tool = db.Column(db.String(50), nullable=False)  # 检测工具
    sample_wafers = db.Column(db.String(100))  # 格式: "1,3,5,7,9"
    machine_type = db.Column(db.String(20), nullable=False)  # 机台类型

    # 可选字段
    image_path = db.Column(db.String(200))  # 图片路径
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Machine {self.machine_id}>'


#
class TestTask(db.Model):
    """压测任务表"""
    id = db.Column(db.Integer, primary_key=True)
    machines_id_lst = db.Column(db.String(100), nullable=False, default="[]")  # 字符串格式的JSON数组
    task_id = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    success_files_generated = db.Column(db.String(500), default=0)
    errors_files = db.Column(db.String(500), default=0)
    total_files = db.Column(db.Integer, default=0)  # 总文件数量
    machine_id = db.Column(db.String(500), nullable=True, default="0")  # 可为 NULL，默认 "0"（字符串）
    batch_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='pending')  # running/completed/cancelled
    progress = db.Column(db.Float, default=0.0)
    current_iteration = db.Column(db.Integer, default=0)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)


    def __repr__(self):
        return f'&lt;TestTask {self.id}&gt;'


class TestResult(db.Model):
    """测试结果表"""
    id = db.Column(db.Integer, primary_key=True)
    test_task_id = db.Column(db.String(100), nullable=False)  # 关联任务ID
    wafer_id = db.Column(db.Integer, nullable=False)  # 芯片ID（晶圆ID）
    file_status = db.Column(db.String(20), default='pending')  # 文件状态：'success', 'failure', 'error'
    image_status = db.Column(db.String(20), default='pending')  # 图片状态：'success', 'failure', 'error'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 结果创建时间
    machine_id = db.Column(db.String(500), nullable=True, default="0")  # 可为 NULL，默认 "0"（字符串）
    iteration = db.Column(db.Integer, default=0)
    def __repr__(self):
        return f'<TestResult wafer_id={self.wafer_id}, file_status={self.file_status}, image_status={self.image_status}>'
