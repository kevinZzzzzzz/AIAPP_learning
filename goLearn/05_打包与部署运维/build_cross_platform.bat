@echo off
chcp 65001 > nul
echo ===================================================================
echo 🛠️ Go 全栈服务自动化打包构建脚本 (Windows 本地 + Linux 交叉编译)
echo ===================================================================

cd ..\03_gin_gorm_api

echo.
echo [1/2] 正在编译 Windows 本地运行可执行文件...
set CGO_ENABLED=0
set GOOS=windows
set GOARCH=amd64
go build -ldflags="-s -w" -o dist\server_windows.exe .
if %errorlevel% neq 0 (
    echo ❌ Windows 构建失败！
    pause
    exit /b %errorlevel%
)
echo ✅ Windows 可执行文件已生成: 03_gin_gorm_api\dist\server_windows.exe

echo.
echo [2/2] 正在跨平台交叉编译 Linux (CentOS/Ubuntu/Debian) 生产二进制文件...
set CGO_ENABLED=0
set GOOS=linux
set GOARCH=amd64
go build -ldflags="-s -w" -o dist\server_linux .
if %errorlevel% neq 0 (
    echo ❌ Linux 交叉编译失败！
    pause
    exit /b %errorlevel%
)
echo ✅ Linux 生产可执行文件已生成: 03_gin_gorm_api\dist\server_linux

echo.
echo ===================================================================
echo 🎉 打包全部完成！
echo 💡 说明: -ldflags="-s -w" 参数去除了符号表和调试信息，二进制体积减小 40%%！
echo 🚀 Linux 二进制文件可直接通过 scp/ftp 传到云服务器，赋予执行权限后直接运行！
echo ===================================================================
pause

