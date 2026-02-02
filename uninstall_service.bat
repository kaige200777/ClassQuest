@echo off
REM Windows服务卸载脚本
REM 安全移除已安装的Windows服务

echo 正在卸载Windows服务...

REM 检查虚拟环境
if not exist "venv\Scripts\python.exe" (
    echo 错误：未找到虚拟环境
    pause
    exit /b 1
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 创建卸载脚本
echo import sys > uninstall_service.py
echo import win32serviceutil >> uninstall_service.py
echo. >> uninstall_service.py
echo if __name__ == '__main__': >> uninstall_service.py
echo     service_name = 'LearningTaskSystem' >> uninstall_service.py
echo     service_display_name = '学习任务单系统' >> uninstall_service.py
echo. >> uninstall_service.py
echo     # 尝试停止并卸载服务 >> uninstall_service.py
echo     try: >> uninstall_service.py
echo         # 先停止服务 >> uninstall_service.py
echo         try: >> uninstall_service.py
echo             win32serviceutil.StopService(service_name) >> uninstall_service.py
echo             print(f'服务 {service_display_name} 已停止') >> uninstall_service.py
echo         except Exception as e: >> uninstall_service.py
echo             print(f'停止服务失败或服务未运行：{e}') >> uninstall_service.py
echo. >> uninstall_service.py
echo         # 卸载服务 >> uninstall_service.py
echo         win32serviceutil.RemoveService(service_name) >> uninstall_service.py
echo         print(f'服务 {service_display_name} 卸载成功！') >> uninstall_service.py
echo     except Exception as e: >> uninstall_service.py
echo         print(f'卸载服务失败：{e}') >> uninstall_service.py
echo         sys.exit(1) >> uninstall_service.py

REM 运行卸载脚本
python uninstall_service.py

REM 清理临时文件
del uninstall_service.py

echo.
echo 服务卸载完成！
pause