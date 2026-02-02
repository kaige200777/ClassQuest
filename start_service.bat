@echo off
REM 启动Windows服务脚本

echo 正在启动学习任务单系统服务...

REM 尝试启动服务
net start LearningTaskSystem >nul 2>&1
if %errorlevel% equ 0 (
    echo 服务启动成功！
    echo 服务正在后台运行...
) else (
    echo 服务启动失败！
    echo.
    echo 可能的原因：
    echo   1. 服务未安装（请运行 install_service.bat）
    echo   2. 服务已经在运行
    echo   3. 权限不足（请以管理员身份运行）
    echo.
    echo 您可以尝试以下操作：
    echo   - 检查服务状态：sc query LearningTaskSystem
    echo   - 查看服务日志：type logs\app.log
    echo   - 手动启动：python production.py
)

pause