# utils.py
import re
import platform
import asyncio
import logging
import os
import datetime
import glob

INVALID_CHAR_REGEX = re.compile(r'[\\/:*?"<>|]')
MAX_CONCURRENT_DOWNLOADS = 5
MAX_LOG_FILES = 5  # 最大日志文件数量


def sanitize_filename(filename):
    """删除文件名中的非法字符"""
    return INVALID_CHAR_REGEX.sub('_', filename)


def windows_asyncio_fix():
    """解决 Windows 上 aiodns 的兼容性问题"""
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def setup_logger(name):
    """配置日志记录器，接受模块名作为参数, 并且清理旧的log"""
    # 创建 log 文件夹
    log_dir = "log"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 生成日志文件名
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = f"log/log_{timestamp}.txt"

    # 创建 logger 对象
    logger = logging.getLogger(name)  # 使用传入的模块名
    logger.setLevel(logging.DEBUG)

    # 检查是否已经有 handler
    if not logger.handlers:
        # 创建文件处理器
        file_handler = logging.FileHandler(log_filename, encoding="utf-8")

        # 创建格式化器
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s"
        )
        file_handler.setFormatter(formatter)

        # 将处理器添加到 logger
        logger.addHandler(file_handler)

    # --- 日志轮换 ---
    def cleanup_logs(log_dir, max_files):
        """删除旧的日志文件"""
        log_files = glob.glob(os.path.join(log_dir, "log_*.txt"))
        log_files.sort(key=os.path.getmtime, reverse=True)  # 按修改时间排序 (最近的在前)

        if len(log_files) > max_files:
            for log_file in log_files[max_files:]:
                try:
                    os.remove(log_file)
                    logger.info(f"已删除旧的日志文件: {log_file}")
                except OSError as e:
                    logger.error(f"删除日志文件失败: {log_file}, 错误: {e}")
    cleanup_logs(log_dir, MAX_LOG_FILES)
    return logger

