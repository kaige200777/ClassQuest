@echo off
REM Windows服务安装脚本
REM 使用pywin32将Flask应用安装为Windows服务

echo 正在安装Windows服务...

REM 检查虚拟环境
if not exist "venv\Scripts\python.exe" (
    echo 错误：未找到虚拟环境，请先创建虚拟环境
    pause
    exit /b 1
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 安装pywin32（如果未安装）
pip show pywin32 >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装pywin32...
    pip install pywin32
)

REM 创建服务安装脚本
echo import sys > install_service.py
echo import win32serviceutil >> install_service.py
echo import os >> install_service.py
echo. >> install_service.py
echo. >> install_service.py
echo if __name__ == '__main__': >> install_service.py
echo     # 获取当前目录 >> install_service.py
echo     current_dir = os.path.dirname(os.path.abspath(__file__)) >> install_service.py
echo     # 服务配置 >> install_service.py
echo     service_name = 'LearningTaskSystem' >> install_service.py
echo     service_display_name = '学习任务单系统' >> install_service.py
echo     service_description = '学习任务单系统生产服务' >> install_service.py
echo     # 获取Python解释器路径 >> install_service.py
echo     python_exe = os.path.join(current_dir, 'venv', 'Scripts', 'python.exe') >> install_service.py
echo     # 获取应用路径 >> install_service.py
echo     app_path = os.path.join(current_dir, 'production.py') >> install_service.py
echo. >> install_service.py
echo     # 配置服务 >> install_service.py
echo     exe_path = python_exe >> install_service.py
echo     cmd_line = f'"{app_path}"' >> install_service.py
echo     working_dir = current_dir >> install_service.py
echo. >> install_service.py
echo     # 创建服务 >> install_service.py
echo     service = win32serviceutil.Win32Service( >> install_service.py
echo         service_name=service_name, >> install_service.py
echo         service_display_name=service_display_name, >> install_service.py
echo         service_description=service_description, >> install_service.py
echo         exe_path=exe_path, >> install_service.py
echo         cmd_line=cmd_line, >> install_service.py
echo         working_dir=working_dir, >> install_service.py
echo         start_type=win32serviceutil.ServiceStartType.AutoStart, >> install_service.py
echo     ) >> install_service.py
echo. >> install_service.py
echo     # 尝试安装服务 >> install_service.py
echo     try: >> install_service.py
echo         win32serviceutil.InstallService(service) >> install_service.py
echo         print(f'服务 {service_display_name} 安装成功！') >> install_service.py
echo         print(f'服务名称：{service_name}') >> install_service.py
echo         print('服务将自动启动') >> install_service.py
echo     except Exception as e: >> install_service.py
echo         print(f'安装服务失败：{e}') >> install_service.py
echo         sys.exit(1) >> install_service.py

REM 运行安装脚本
python install_service.py

REM 清理临时文件
del install_service.py

echo.
echo 服务安装完成！
echo 您可以使用以下命令管理服务：
echo   启动服务：start_service.bat
echo   停止服务：stop_service.bat
echo   卸载服务：uninstall_service.bat
echo.
pause