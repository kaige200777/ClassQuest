#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产环境启动脚本
使用waitress作为WSGI服务器，替代Flask开发服务器
"""

import os
import sys
import logging
from waitress import serve
from app import app
import config

# 创建logs目录
if not os.path.exists(config.LOG_DIR):
    os.makedirs(config.LOG_DIR)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(config.LOG_DIR, config.LOG_FILE)),
        logging.StreamHandler(sys.stdout)
    ]
)

# 启动waitress服务器
if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logger.info(f"Starting production server on {config.HOST}:{config.PORT}")
    logger.info(f"Threads: {config.WAITRESS_THREADS}")
    
    serve(
        app,
        host=config.HOST,
        port=config.PORT,
        threads=config.WAITRESS_THREADS,
        connection_limit=config.WAITRESS_CONNECTION_LIMIT,
        send_bytes=config.WAITRESS_SEND_BYTES,
        url_scheme='http',
        url_prefix=''
    )