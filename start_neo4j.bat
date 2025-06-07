@echo off
echo 🚀 启动Neo4j数据库...
echo.

REM 检查Docker是否运行
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker未运行，请先启动Docker Desktop
    pause
    exit /b 1
)

REM 停止并删除已存在的容器（如果有）
docker stop neo4j-kg >nul 2>&1
docker rm neo4j-kg >nul 2>&1

REM 启动Neo4j容器
echo 📦 启动Neo4j容器...
docker run -d --name neo4j-kg -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest

if %errorlevel% equ 0 (
    echo.
    echo ✅ Neo4j启动成功！
    echo 📊 Web界面: http://localhost:7474
    echo 🔌 数据库连接: bolt://localhost:7687
    echo 👤 用户名: neo4j
    echo 🔑 密码: password
    echo.
    echo ⏳ 请等待30秒让Neo4j完全启动...
    timeout /t 30 /nobreak >nul
    echo.
    echo 🎉 Neo4j已准备就绪！
) else (
    echo ❌ Neo4j启动失败
)

pause 