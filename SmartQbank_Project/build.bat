@echo off
echo =========================================
echo       SmartQbank 一键打包脚本
echo =========================================

echo [1/3] 正在检查并安装必要依赖...
pip install -r requirements.txt
pip install flet pyinstaller

echo [2/3] 正在准备构建环境...
if not exist "assets" mkdir assets
REM 如果没有 logo.ico，则跳过图标打包
if not exist "assets\logo.ico" (
    echo 未找到 assets\logo.ico，将使用默认图标。
    set ICON_FLAG=
) else (
    set ICON_FLAG=--icon assets\logo.ico
)

echo [3/3] 开始执行 flet pack...
flet pack main_desktop.py --name "SmartQbank" %ICON_FLAG%

echo =========================================
echo 打包完成！请在 dist\ 目录下查找生成的 .exe 文件。
echo 运行 .exe 时，系统会自动在其同级目录下创建 data\ 文件夹存储数据。
echo =========================================
pause
