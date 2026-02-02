@echo off
REM 停止Windows服务脚本

echo 正在停止学习任务单系统服务...

REM 尝试停止服务
net stop LearningTaskSystem >nul 2>&1
if %errorlevel% equ 0 (
    echo 服务停止成功！
) else (
    echo 服务停止失败！
    echo.
    echo 可能的原因：
    echo   1. 服务未安装
    echo   2. 服务已经停止
    echo   3. 权限不足（请以管理员身份运行）
    echo.
    echo 您可以尝试以下操作：
    echo   - 检查服务状态：sc query LearningTaskSystem
    echo   - 查看服务日志：type logs\app.log
)

pause