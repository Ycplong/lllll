# 系统内置包
import os
import random
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta


from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_migrate import Migrate
from PIL import Image
from sqlalchemy import and_
from werkzeug.utils import secure_filename


from common.util import (CustomLogger,
                        process_sample_wafers)
from models import db, Machine, TestResult, TestTask
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'machines.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB
logger = CustomLogger().get_logger()
# 限制并发任务数量和接口访问频率
MAX_CONCURRENT_TASKS = 10  # 最大并发任务数量
MAX_REQUESTS_PER_MINUTE = 5  # 每分钟最多请求次数
MAX_REQUESTS_FUN_PER_MINUTE = 10
# 记录接口请求次数（简化版：使用内存中计数）
requests_count = 0
requests_func_count = 0
last_request_time = time.time()
last_fun_request_time = time.time()
# 控制并发线程池
executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TASKS)
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'max_overflow': 5,
    'pool_timeout': 30,
    'pool_pre_ping': True
}
db.init_app(app)
migrate = Migrate(app, db)  # 新增此行，必须在 db.init_app(app) 之后
with app.app_context():
    db.create_all()



# 机台配置
MACHINES = {
    "aoi01": {"type": "sem"},
    "aoi02": {"type": "sem"},
    "ins02": {"type": "om"},
    "ins01": {"type": "om"},
    "review01": {"type": "om"},
    "review02": {"type": "om"}
}

# 生产流程定义
PIPELINE = ["aoi01", "aoi01", "aoi02", "ins02", "review01", "ins01", "review01"]


@app.route('/api/machines_id_lst', methods=['GET', 'POST'])
def machines_id_lst():
    if request.method == 'GET':
        # 构建查询并使用 limit 或分页来优化性能（假设你有大量数据）
        query = Machine.query.all()  # 获取所有机台数据

        # 提取 machine_id
        machine_id_lst = [m.machine_id for m in query]

        # 返回结果
        return jsonify({"machine_id_lst": machine_id_lst})

    # 处理 POST 请求逻辑（如果需要）
    return jsonify({"error": "Invalid request method"}), 405


# 获取分页机台列表
@app.route('/api/machines', methods=['GET', 'POST'])
def machine_list():
    if request.method == 'GET':
        """获取分页机台列表"""
        # 获取分页参数，默认为第1页，每页10条
        print(request.args)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        product_id = request.args.get('product_id')
        step_id = request.args.get('step_id')

        # 构建查询
        query = Machine.query
        if product_id:
            query = query.filter(Machine.product_id.ilike(f'%{product_id}%'))
        if step_id:
            query = query.filter(Machine.step_id.ilike(f'%{step_id}%'))


        # 计算分页偏移量
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        machines = pagination.items

        # 构建返回数据
        return jsonify({
            'items': [{
                'id': m.id,
                'machine_id': m.machine_id,
                'product_id': m.product_id,
                'step_id': m.step_id,
                'recipe_id': m.recipe_id,
                'review_id': m.review_id,
                'review_tool': m.review_tool,
                'inspection_tool': m.inspection_tool,
                'sample_wafers': m.sample_wafers,
                'machine_type': m.machine_type,
                'created_at': m.created_at.isoformat() if m.created_at else None,
                'updated_at': m.updated_at.isoformat() if m.updated_at else None
            } for m in machines],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': pagination.page,
            'per_page': pagination.per_page
        })



#获取单个机台详情
@app.route('/api/machine/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def machine_resource(id):
    machine = Machine.query.get_or_404(id)  # 修正参数名从machine_id改为id

    if request.method == 'GET':
        """获取单个机台详情"""
        return jsonify({
            'id': machine.id,
            'machine_id': machine.machine_id,
            'product_id': machine.product_id,
            'step_id': machine.step_id,
            'recipe_id': machine.recipe_id,
            'review_id': machine.review_id,
            'review_tool': machine.review_tool,
            'inspection_tool': machine.inspection_tool,
            'sample_wafers': machine.sample_wafers,
            'machine_type': machine.machine_type,
            'image_path': machine.image_path,
            'created_at': machine.created_at.isoformat() if machine.created_at else None,
            'updated_at': machine.updated_at.isoformat() if machine.updated_at else None
        })



#添加新的机台
@app.route('/api/add_machine', methods=['POST'])
def add_machine():
    """添加新的机台"""
    data = request.get_json()
    print(data)
    # 必填字段验证
    required_fields = ['product_id', 'step_id', 'recipe_id', 'review_id',
                       'review_tool', 'inspection_tool', 'machine_type','sample_wafers']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'字段 {field} 不能为空'}), 400

    # 验证 sample_wafers 格式
    sample_wafers = data.get('sample_wafers')
    if sample_wafers:
        try:
            wafers = list(map(int, sample_wafers.split(',')))
            if len(wafers) > 5:
                return jsonify({'error': '最多选择5个芯片ID'}), 400
            if any(w < 1 or w > 25 for w in wafers):
                return jsonify({'error': '请选择1-25的整数'}), 400
            if len(wafers) != len(set(wafers)):  # 确保晶片ID唯一
                return jsonify({'error': '晶片ID不能重复'}), 400
        except ValueError:
            return jsonify({'error': 'sample_wafers格式错误，应为逗号分隔的数字'}), 400
    else:
        return jsonify({'error': 'sample_wafers不能为空'}), 400

    # 验证 machine_type 是否有效
    valid_machine_types = ['SEM', 'AOI']
    if data['machine_type'] not in valid_machine_types:
        return jsonify({'error': f'无效的机台类型，必须是: {", ".join(valid_machine_types)}'}), 400

    # 创建新的机台
    new_machine = Machine(
        machine_id = data['machine_id'],
        product_id=data['product_id'],
        step_id=data['step_id'],
        recipe_id=data['recipe_id'],
        review_id=data['review_id'],
        review_tool=data['review_tool'],
        inspection_tool=data['inspection_tool'],
        machine_type=data['machine_type'],
        sample_wafers=sample_wafers,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    try:
        db.session.add(new_machine)
        db.session.commit()
        return jsonify({
            'message': '机台添加成功',
            'id': new_machine.id,
            'machine_id': new_machine.machine_id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'添加失败: {str(e)}'}), 500


# 修改操作：需要 id
@app.route('/api/update_machine/<int:id>', methods=['PUT'])
def update_machine(id):
    """更新机台信息"""
    machine = Machine.query.get_or_404(id)
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400
    # 必填字段验证
    required_fields = ['product_id', 'step_id', 'recipe_id', 'review_id',
                       'review_tool', 'inspection_tool', 'machine_type']
    for field in required_fields:
        if field in data and not data[field]:
            return jsonify({'error': f'字段 {field} 不能为空'}), 400

    # 验证 sample_wafers 格式
    sample_wafers = data.get('sample_wafers', machine.sample_wafers)
    if sample_wafers:
        try:
            wafers = list(map(int, sample_wafers.split(',')))
            if len(wafers) > 5:
                return jsonify({'error': '最多选择5个芯片ID'}), 400
            if any(w < 1 or w > 25 for w in wafers):
                return jsonify({'error': '请选择1-25的整数'}), 400
            # 确保晶片ID唯一
            if len(wafers) != len(set(wafers)):
                return jsonify({'error': '晶片ID不能重复'}), 400
        except ValueError:
            return jsonify({'error': 'sample_wafers格式错误，应为逗号分隔的数字'}), 400
    else:
        return jsonify({'error': 'sample_wafers不能为空'}), 400

    # 验证 machine_type 是否有效
    valid_machine_types = ['SEM', 'AOI']
    if 'machine_type' in data and data['machine_type'] not in valid_machine_types:
        return jsonify({'error': f'无效的机台类型，必须是: {", ".join(valid_machine_types)}'}), 400

    # 更新字段
    for field in required_fields:
        if field in data:
            setattr(machine, field, data[field])

    machine.sample_wafers = sample_wafers
    machine.updated_at = datetime.utcnow()

    try:
        db.session.commit()
        return jsonify({
            'message': '机台更新成功',
            'id': machine.id,
            'machine_id': machine.machine_id,
            'updated_at': machine.updated_at.isoformat()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'更新失败: {str(e)}'}), 500


# 删除操作：需要 id
@app.route('/api/delete_machine/<int:id>', methods=['DELETE'])
def delete_machine(id):
    """删除机台"""
    machine = Machine.query.get_or_404(id)

    try:
        # 检查是否有关联数据
        if machine:
            db.session.delete(machine)
            db.session.commit()
            return jsonify({
                'message': '机台删除成功',
                'id': id
            }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'删除失败: {str(e)}'}), 500





#创建功能测试任务api
@app.route('/api/start_function_test', methods=['POST'])
def create_function_task():
    """创建功能测试任务"""
    global requests_func_count, last_fun_request_time

    current_time = time.time()
    # 检查请求内容类型
    if not request.is_json:
        app.logger.error(f"无效的Content-Type: {request.content_type}")
        return jsonify({
            "success": False,
            "error": "Content-Type must be application/json"
        }), 415
    logger.info(f"请求参数{request.get_json()}")
    # 日志记录请求到达时间
    # 计算每分钟的请求次数
    if current_time - last_fun_request_time > 60:  # 超过一分钟，重置请求计数
        requests_func_count = 0
        last_fun_request_time = current_time
        logger.info(f"一分钟已过，重置请求计数器。当前时间: {current_time}")

    # 限制每分钟请求次数
    if requests_func_count >= MAX_REQUESTS_FUN_PER_MINUTE:
        logger.warning(f"请求过于频繁，每分钟超过最大请求次数: {MAX_REQUESTS_FUN_PER_MINUTE}")
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429

    data = request.get_json()

    # 验证必要字段
    if not all(k in data for k in ['machine_id', 'batch_count']):
        return jsonify({'error': '缺少必要字段'}), 400


    # 生成任务ID
    task_id = str(uuid.uuid4())
    machine_id = data['machine_id']
    batch_count = data['batch_count']
    logger.info(f"生成任务ID: {task_id}")
    print(f"请求参数{request.get_json()}")
    # 创建功能测试任务并保存到数据库
    task_info = TestTask(
        task_id=task_id,
        machine_id=machine_id,
        batch_count=batch_count
    )
    machine_data = {
        'task_id': task_info.task_id,
        'machine_id': task_info.machine_id,
        'batch_count': task_info.batch_count
        # 添加其他需要的字段
    }
    # machine_data = task_info.__dict__
    print(f"machine_data:{machine_data}")
    db.session.add(task_info)
    db.session.commit()

    # 启动功能测试任务线程
    threading.Thread(target=run_func_test, args=(machine_data,)).start()

    # 增加请求计数
    requests_func_count += 1
    logger.info(f"请求计数增加，当前计数: {last_fun_request_time}")

    return jsonify({'message': '功能测试任务创建成功', 'task_id': task_id}), 201


def run_func_test(task_info):
    """执行功能测试任务"""
    with app.app_context():  # 确保在后台线程中有Flask应用上下文
        try:
            print(f"task_info:{task_info}")
            machine_id = task_info['machine_id']
            task_id = task_info['task_id']
            batch_count = int(task_info['batch_count'])  # 确保是整数

            # 查询任务
            task = db.session.query(TestTask).filter(
                and_(
                    TestTask.machine_id == machine_id,
                    TestTask.task_id == task_id
                )
            ).first()
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return

            # 查询机器信息
            machine = db.session.query(Machine).filter(
                Machine.machine_id == machine_id
            ).first()
            if not machine:
                logger.error(f"机器不存在: {machine_id}")
                return
            wafer_id_lst = process_sample_wafers(machine)
            # 初始化计数器
            file_success = 0
            file_failure = 0
            file_error = 0

            logger.info(f"开始处理任务 {task_id}，机台ID: {machine_id}")

            for i in range(batch_count):
                for wafer_id in wafer_id_lst:
                    try:
                        # 生成文件路径
                        file_path = f"/path/to/files/{machine_id}_{wafer_id}_file.txt"
                        image_path = f"/path/to/images/{machine_id}_{wafer_id}_image.png"

                        # 模拟处理结果
                        if random.random() < 0.5:  # 50%成功率
                            file_status = 'success' if random.random() < 0.5 else 'failure'
                            image_status = 'success' if random.random() < 0.5 else 'failure'
                        else:
                            file_status = 'error'
                            image_status = 'error'

                        # 更新计数器
                        if file_status == 'success':
                            file_success += 1
                        elif file_status == 'failure':
                            file_failure += 1
                        else:
                            file_error += 1

                        # 记录结果
                        test_result = TestResult(
                            test_task_id=task.id,
                            wafer_id=wafer_id,
                            file_status=file_status,
                            image_status=image_status,
                            machine_id=machine_id
                        )
                        db.session.add(test_result)
                        db.session.commit()

                    except Exception as e:
                        logger.exception(f"处理晶圆 {wafer_id} 时出现异常: {e}")
                        db.session.rollback()

            # 更新任务统计
            total_operations = len(wafer_id_lst) * batch_count * 2  # 每个晶圆有文件和图片
            task.total_files = total_operations
            task.success_files_generated = file_success
            task.errors_files = file_failure + file_error
            task.success_rate = file_success / total_operations if total_operations > 0 else 0
            db.session.commit()

            logger.info(
                f"任务 {task.id} 完成: 成功 {file_success}, 失败 {file_failure}, "
                f"错误 {file_error}, 成功率 {task.success_rate:.2%}"
            )

        except Exception as e:
            logger.exception(f"任务处理过程中出现未捕获的异常: {e}")



@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """获取压测任务状态"""
    task = TestTask.query.get_or_404(task_id)
    return jsonify({
        'id': task.id,
        'machine_ids': task.machine_ids.split(','),
        'start_time': task.start_time.isoformat(),
        'end_time': task.end_time.isoformat(),
        'status': task.status,
        'files_generated': task.files_generated,
        'errors_count': task.errors_count,
        'created_at': task.created_at.isoformat(),
        'completed_at': task.completed_at.isoformat() if task.completed_at else None
    })

# 看板数据API
@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """获取看板统计数据"""
    # 查询所有测试结果
    all_results = TestResult.query.all()
    # 初始化计数器
    total_files = len(all_results) * 2  # 每个结果有文件和图片两个状态
    success_files = 0
    failure_files = 0
    error_files = 0  # 统计各类状态

    for result in all_results:
        # 统计文件状态
        if result.file_status == 'success':
            success_files += 1
        elif result.file_status == 'failure':
            failure_files += 1
        elif result.file_status == 'error':
            error_files += 1

        # 统计图片状态
        if result.image_status == 'success':
            success_files += 1
        elif result.image_status == 'failure':
            failure_files += 1
        elif result.image_status == 'error':
            error_files += 1
    # 计算成功率（成功数/总数）
    success_rate = round((success_files / total_files) * 100, 2) if total_files > 0 else 0
    data = {
        'files_generated': total_files,
        'success_files': success_files,
        'failure_files': failure_files,
        'error_files': error_files,
        'success_rate': success_rate,
        'last_updated': datetime.utcnow().isoformat()  # 添加最后更新时间
    }
    print(data)
    return jsonify(data)


@app.route('/api/stress_test', methods=['POST'])
def stress_test_api():
    """压力测试API"""
    global requests_count, last_request_time

    current_time = time.time()
    logger.info(f"收到请求，当前时间: {current_time}")

    # 请求频率控制
    if current_time - last_request_time > 60:
        requests_count = 0
        last_request_time = current_time
        logger.info(f"一分钟已过，重置请求计数器。当前时间: {current_time}")

    if requests_count >= MAX_REQUESTS_PER_MINUTE:
        logger.warning(f"请求过于频繁，每分钟超过最大请求次数: {MAX_REQUESTS_PER_MINUTE}")
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429

    data = request.json
    if not data or 'machines' not in data:
        logger.error("机台列表为空或缺失")
        return jsonify({'message': '机台列表不能为空'}), 400

    # 计算测试持续时间（秒）
    try:
        start_time = datetime.fromisoformat(data["start_time"])
        end_time = datetime.fromisoformat(data["end_time"])
        duration_seconds = (end_time - start_time).total_seconds()

        if duration_seconds <= 0:
            return jsonify({'message': '结束时间必须晚于开始时间'}), 400
    except Exception as e:
        logger.error(f"时间格式错误: {e}")
        return jsonify({'message': '时间格式不正确，请使用ISO格式'}), 400

    machines_id_lst = data['machines']
    if not machines_id_lst:
        logger.error("机台列表为空")
        return jsonify({'message': '机台列表不能为空'}), 400

    # 创建任务ID和任务信息
    task_id = str(uuid.uuid4())
    logger.info(f"生成任务ID: {task_id}")

    task_info = TestTask(
        task_id=task_id,
        machines_id_lst=str(machines_id_lst),
        start_time=start_time,
        end_time=end_time,
        status='running'
    )
    db.session.add(task_info)
    db.session.commit()

    # 启动持续压力测试线程
    threading.Thread(
        target=run_continuous_stress_test,
        args=(machines_id_lst, duration_seconds, task_id),
        daemon=True
    ).start()

    requests_count += 1
    logger.info(f"请求计数增加，当前计数: {requests_count}")

    return jsonify({
        'message': f'压力测试已开始，将持续{duration_seconds / 60:.1f}分钟',
        'task_id': task_id,
        'duration_minutes': duration_seconds / 60
    })


def run_continuous_stress_test(machines, duration_seconds, task_id):
    """持续运行压力测试直到达到指定时长"""
    with app.app_context():  # 添加应用上下文

        end_time = time.time() + duration_seconds
        iteration = 0

        while time.time() < end_time and not app.config.get('SHUTDOWN_FLAG'):
            iteration += 1
            logger.info(f"开始第{iteration}轮压力测试 (剩余时间: {end_time - time.time():.0f}秒)")

            futures = []

            for machine_id in machines:
                machine = db.session.query(Machine).filter_by(machine_id=machine_id).first()
                if machine:
                    remaining_time = end_time - time.time()
                    future = executor.submit(
                        stress_test,
                        {
                            **machine.__dict__,
                            "task_id": task_id,
                            "iteration": iteration,
                            "remaining_time": remaining_time
                        }
                    )
                    futures.append(future)

            # 等待本轮所有任务完成
            for future in futures:
                try:
                    future.result(timeout=3600)  # 每个任务最多1小时
                except Exception as e:
                    logger.error(f"任务执行失败: {e}")

            # 更新任务进度
            try:
                task = TestTask.query.filter_by(task_id=task_id).first()
                if task:
                    elapsed = time.time() - (end_time - duration_seconds)
                    task.progress = min(100, 100 * elapsed / duration_seconds)
                    task.current_iteration = iteration
                    db.session.commit()
            except Exception as e:
                logger.error(f"更新任务进度失败: {e}")

            # 检查是否需要提前终止
            task = TestTask.query.filter_by(task_id=task_id).first()
            if task and task.status == 'cancelled':
                logger.info(f"任务 {task_id} 已被取消")
                break

            time.sleep(10)  # 每轮间隔10秒

        # 标记任务完成
        try:
            task = TestTask.query.filter_by(task_id=task_id).first()
            if task:
                task.status = 'completed' if time.time() >= end_time else 'interrupted'
                task.end_time = datetime.utcnow()
                db.session.commit()
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")

        logger.info(f"压力测试任务 {task_id} 已完成")


def stress_test(machine_data):
    """单次压力测试逻辑"""
    with app.app_context():
        try:
            machine_id = machine_data['machine_id']
            iteration = machine_data.get('iteration', 0)
            task_id = machine_data['task_id']
            remaining_time = machine_data.get("remaining_time", None)
            if remaining_time:
                logger.info(
                    f"[线程 {threading.current_thread().name}] 机台 {machine_id} 正在执行第 {iteration} 轮压力测试，剩余时间约 {remaining_time:.1f} 秒")
            # 安全处理晶圆列表
            wafer_id_lst = []
            if 'sample_wafers' in machine_data:
                try:
                    if isinstance(machine_data['sample_wafers'], str):
                        wafer_id_lst = eval(machine_data['sample_wafers'])
                    elif isinstance(machine_data['sample_wafers'], list):
                        wafer_id_lst = machine_data['sample_wafers']
                except Exception as e:
                    logger.error(f"解析晶圆列表失败: {e}")

            task = TestTask.query.filter_by(task_id=task_id).first()
            if not task:
                logger.error(f"任务ID {task_id} 不存在")
                return

            # 模拟处理每个芯片
            for wafer_id in wafer_id_lst:

                status = random.choices(
                    ['success', 'failure', 'error'],
                    weights=[0.5, 0.3, 0.2],
                    k=1
                )[0]

                # 存储结果
                test_result = TestResult(
                    test_task_id=task.id,
                    wafer_id=wafer_id,
                    file_status=status,
                    machine_id=machine_id,
                    iteration=iteration
                )
                db.session.add(test_result)

            db.session.commit()

        except Exception as e:
            logger.error(f"压力测试出错: {e}")
            db.session.rollback()




# 页面路由
@app.route('/')
def index():
    """站点信息页面"""
    return render_template('index.html')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    """数据看板页面"""
    return render_template('dashboard.html')

@app.route('/function_test')
def function_test():
    """功能测试页面"""
    return render_template('function_test.html')
    

@app.route('/stress_test')
def stress_test_():
    """压测功能页面"""
    return render_template('stress_test.html')

@app.route('/site_info')
def site_info():
    machines = Machine.query.all()
    return render_template('machine_list.html', machines=machines)

# def generate_wafer(wafer_id):
#     """生成晶圆数据"""
#     return {
#         "wafer_id": wafer_id,
#         "batch_id": f"BATCH-{random.randint(1000,9999)}",
#         "creation_time": datetime.now().isoformat(),
#         "status": "initial",
#         "thickness": round(random.uniform(0.5, 1.0), 3),
#         "defects": random.randint(0, 5),
#         "material": random.choice(["Silicon", "GaAs", "InP"]),
#         "processing_log": []
#     }

# def process_wafer(wafer, machine):
#     """处理晶圆数据"""
#     # 记录处理日志
#     log_entry = {
#         "machine": machine,
#         "time": datetime.now().isoformat(),
#         "result": None
#     }
#
#     # AOI机台处理
#     if machine.startswith("aoi"):
#         if "aoi_passed" not in wafer:
#             # 第一次AOI检测，随机通过10/25
#             wafer["aoi_passed"] = random.random() < (10/25)
#         log_entry["result"] = "passed" if wafer["aoi_passed"] else "failed"
#
#     # INS/Review机台处理
#     elif machine.startswith("ins") or machine.startswith("review"):
#         if "ins_passed" not in wafer:
#             # 从通过的10个中随机通过5个
#             wafer["ins_passed"] = wafer.get("aoi_passed", False) and random.random() < 0.5
#         log_entry["result"] = "passed" if wafer["ins_passed"] else "failed"
#
#     wafer["processing_log"].append(log_entry)
#     wafer["status"] = f"{log_entry['result']}_{machine}"
#     return wafer["status"].startswith("passed")

# @app.route('/generate', methods=['POST'])
# def generate_data():
#     """生成模拟数据API"""
#     data = request.json
#     lot = data.get('lot', 1)
#     dur = data.get('dur', 0)
#
#     if dur > 0:
#         # 持续生成模式
#         def generate_continuously():
#             while True:
#                 generate_batch()
#                 time.sleep(dur)
#         threading.Thread(target=generate_continuously).start()
#         return jsonify({"status": "started", "message": f"Continuous generation every {dur} seconds"})
#     else:
#         # 批量生成模式
#         results = [generate_batch() for _ in range(lot)]
#         return jsonify(results)
#
# def generate_batch():
#     """生成一批数据"""
#     # 生成25个晶圆
#     wafers = [generate_wafer(i+1) for i in range(25)]
#
#     # 按pipeline处理
#     for machine in PIPELINE:
#         for wafer in wafers:
#             if not process_wafer(wafer, machine):
#                 break  # 失败则不再继续后续流程
#
#     return {
#         "batch_id": f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}",
#         "timestamp": datetime.now().isoformat(),
#         "wafers": wafers,
#         "machine_stats": {
#             m: sum(1 for w in wafers if w["status"].endswith(m))
#             for m in PIPELINE
#         }
#     }


@app.route('/api/machines/upload', methods=['POST'])
def upload_machine_image():
    """上传机台图片"""
    if 'file' not in request.files:
        return jsonify({'error': '未提供文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    # 创建上传目录
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    try:
        # 使用PIL打开并验证图片
        with Image.open(file.stream) as img:
            print(f"Image format: {img.format}, Size: {img.size}")

            # 验证尺寸
            if img.size != (680, 680):
                return jsonify({'error': '请上传680x680像素的图片'}), 400

            # 转换为RGB模式（避免alpha通道问题）
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # 生成安全的文件名
            ext = 'jpg'  # 统一保存为jpg格式
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # 保存图片（确保质量为100%）
            img.save(filepath, 'JPEG', quality=100)
            print(f"Image saved to: {filepath}")

            # 验证文件是否确实存在
            if not os.path.exists(filepath):
                return jsonify({'error': '文件保存失败'}), 500

            return jsonify({
                'message': '图片上传成功',
                'filename': filename,
                'path': f"/uploads/{filename}"  # 返回可访问的URL路径
            })

    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return jsonify({'error': '图片处理失败', 'details': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)