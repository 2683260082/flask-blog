@echo off
chcp 65001 >nul
rem ============================================================
rem 墨刊 - 个人博客 一键启动脚本
rem 功能: 检查 Python 环境 -> 检查/自动安装依赖 -> 启动服务
rem       -> 延迟自动打开浏览器
rem 本窗口不要关闭, 关闭即停止服务
rem ============================================================

rem 切换到本脚本所在目录, 保证从任何位置双击都能正常找到文件
cd /d "%~dp0"

rem 程序入口就在本目录下的 app.py
if not exist "app.py" goto :src_missing

echo.
echo  ====================================================
echo       墨刊个人博客  -  正在启动
echo  ====================================================
echo.

rem --- 检查 Python 是否可用 ---
python --version >nul 2>&1
if errorlevel 1 goto :no_python

rem --- 检查依赖是否已安装 (Flask + Markdown + Pygments) ---
python -c "import flask, markdown, pygments" >nul 2>&1
if errorlevel 1 goto :no_deps

echo  [1/3] 环境检查通过
echo  [2/3] 正在启动服务...
echo.
echo  ----------------------------------------------------
echo   博客前台:  http://127.0.0.1:5000
echo   管理后台:  http://127.0.0.1:5000/admin
echo   后台账号:  admin / admin123
echo  ----------------------------------------------------
echo   浏览器约 5 秒后自动打开前台
echo   若页面暂时打不开, 等几秒按 F5 刷新即可
echo  ----------------------------------------------------
echo.

rem 用独立小窗口延迟约 5 秒后打开浏览器, 打开后该小窗口自动关闭。
rem 之所以不直接 start: 服务尚未就绪时会连接失败。
start "auto-open-browser" cmd /c "ping -n 6 127.0.0.1 >nul && start http://127.0.0.1:5000"

rem 在当前窗口启动服务。关闭本窗口或按 Ctrl+C 即停止服务。
python app.py
goto :end

rem --- 程序入口缺失(文件夹被改名或移动) ---
:src_missing
echo.
echo  [错误] 找不到程序入口 app.py。
echo.
echo  请确认本 .bat 文件与 app.py 放在同一目录下,
echo  且不要单独复制本 .bat 文件到别处运行。
echo.
pause
goto :end

rem --- 未检测到 Python ---
:no_python
echo.
echo  [错误] 没有检测到 Python 环境。
echo.
echo  请先安装 Python 3.9 或更高版本:
echo    1. 打开 https://www.python.org/downloads/ 下载
echo    2. 安装时务必勾选 "Add Python to PATH"  ^<-- 这一步最关键
echo    3. 安装完成后重新双击本文件
echo.
pause
goto :end

rem --- 未安装依赖 ---
:no_deps
echo  [1/3] 环境检查通过
echo  [2/3] 未检测到项目依赖, 正在自动安装...
echo.
python -m pip install -r requirements.txt
if errorlevel 1 goto :install_failed
echo.
echo  依赖安装完成, 正在启动服务...
echo.
echo  ----------------------------------------------------
echo   博客前台:  http://127.0.0.1:5000
echo   管理后台:  http://127.0.0.1:5000/admin
echo   后台账号:  admin / admin123
echo  ----------------------------------------------------
echo   浏览器约 5 秒后自动打开前台
echo  ----------------------------------------------------
echo.
start "auto-open-browser" cmd /c "ping -n 6 127.0.0.1 >nul && start http://127.0.0.1:5000"
python app.py
goto :end

rem --- 依赖安装失败 ---
:install_failed
echo.
echo  [错误] 依赖自动安装失败, 可能是网络原因。
echo  请在本文件所在目录内执行下面这条命令后, 重新双击本文件:
echo.
echo      pip install -r requirements.txt
echo.
echo  如果下载很慢, 可换用国内镜像:
echo.
echo      pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
echo.
pause

:end
