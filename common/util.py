
import logging
import os

import colorlog
from logging.handlers import RotatingFileHandler
import inspect

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    """检查文件扩展名是否为允许的格式"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_sample_wafers(machine):
    """安全处理machine.sample_wafers字段，返回晶圆列表"""
    try:
        if not hasattr(machine, 'sample_wafers'):
            return []
        if isinstance(machine.sample_wafers, list):
            return machine.sample_wafers

        if isinstance(machine.sample_wafers, str):
            return eval(machine.sample_wafers) if machine.sample_wafers else []
        return []
    except Exception as e:
        print(f"处理sample_wafers出错: {e}")
        return []


class SimpleFlaskLogger:
    """
    简化版 Flask 日志工具，支持全局访问和大写方法调用
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SimpleFlaskLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self, log_dir='logs', log_filename=None, max_log_size=10 * 1024 * 1024, backup_count=5):
        """
        初始化自定义日志记录器

        :param log_dir: 日志文件保存的目录，默认为'logs'
        :param log_filename: 日志文件的名称，默认为当前日期的日志文件
        :param max_log_size: 日志文件的最大大小，超过该大小后会进行日志轮换，单位字节
        :param backup_count: 保留的日志文件备份数量
        """
        # 创建日志目录（如果不存在）
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 如果没有传入日志文件名，默认使用当前日期
        if log_filename is None:
            log_filename = f"{os.path.basename(__file__).split('.')[0]}_{os.getpid()}.log"

        # 设置日志文件路径
        self.log_path = os.path.join(log_dir, log_filename)

        # 创建日志记录器
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)  # 设置日志记录器的最小日志级别

        # 创建日志格式化器（包括颜色格式）
        log_format = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s - [Function: %(custom_funcName)s]',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'magenta',
            }
        )

        # 创建文件处理器（支持日志轮换）
        file_handler = RotatingFileHandler(self.log_path, maxBytes=max_log_size, backupCount=backup_count,
                                           encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s - [Function: %(custom_funcName)s]'))
        file_handler.setLevel(logging.DEBUG)

        # 创建控制台处理器（带颜色）
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_format)
        console_handler.setLevel(logging.DEBUG)  # 控制台显示DEBUG级别及以上日志

        # 将处理器添加到记录器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def get_logger(self):
        """
        返回日志记录器实例
        """
        return self.logger

    def _log(self, level, msg, *args, **kwargs):
        """安全的日志记录方法"""
        # 获取当前函数的名称
        frame = inspect.currentframe().f_back
        function_name = frame.f_code.co_name  # 获取调用者的函数名称

        # 将函数名称加入到 extra 参数中
        extra = {"custom_funcName": function_name}

        # 移除可能冲突的extra参数
        kwargs.pop('extra', None)

        # 记录日志
        self.logger.log(level, msg, *args, extra=extra, **kwargs)

    # 添加大写的日志方法
    def DEBUG(self, msg, *args, **kwargs):
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def INFO(self, msg, *args, **kwargs):
        self._log(logging.INFO, msg, *args, **kwargs)

    def WARNING(self, msg, *args, **kwargs):
        self._log(logging.WARNING, msg, *args, **kwargs)

    def ERROR(self, msg, *args, **kwargs):
        self._log(logging.ERROR, msg, *args, **kwargs)

    def CRITICAL(self, msg, *args, **kwargs):
        self._log(logging.CRITICAL, msg, *args, **kwargs)



