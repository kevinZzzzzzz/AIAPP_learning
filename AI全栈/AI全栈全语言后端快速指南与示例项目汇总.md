# 🌐 AI 全栈多语言后端示例项目与全流程指南汇总

欢迎来到 AI 全栈后端开发营！这里为你提供了主流的 3 大后端语言（**Java**、**Python**、**Go**）的标准全栈后端示例项目与专属全流程指南文件。

---

## 📂 3 大全栈后端示例项目概览

| 语言框架 | 项目目录 | 配置文件 / 端口 | 本地数据库 | 专属搭建与部署指南 |
| :--- | :--- | :--- | :--- | :--- |
| **Java** (Spring Boot 3 + JPA) | [**`java-backend-demo`**](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/AI%E5%85%A8%E6%A0%88/java-backend-demo) | `application.yml`<br/>端口: `8080` | H2 内存数据库<br/>(含控制台 `/h2-console`) | [📘 Java 从零搭建到部署全流程指南.md](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/AI%E5%85%A8%E6%A0%88/Java%E5%90%8E%E7%AB%AF%E4%BB%8E%E9%9B%B6%E6%90%AD%E5%BB%BA%E5%88%B0%E9%83%A8%E7%BD%B2%E5%85%A8%E6%B5%81%E7%A8%8B%E6%8C%87%E5%8D%97.md) |
| **Python** (FastAPI + SQLAlchemy) | [**`python-backend-demo`**](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/AI%E5%85%A8%E6%A0%88/python-backend-demo) | `main.py`<br/>端口: `8000` | SQLite 文件<br/>(`sql_app.db`) | [📘 Python 从零搭建到部署全流程指南.md](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/AI%E5%85%A8%E6%A0%88/Python%E5%90%8E%E7%AB%AF%E4%BB%8E%E9%9B%B6%E6%90%AD%E5%BB%BA%E5%88%B0%E9%83%A8%E7%BD%B2%E5%85%A8%E6%B5%81%E7%A8%8B%E6%8C%87%E5%8D%97.md) |
| **Go** (Gin + GORM) | [**`go-backend-demo`**](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/AI%E5%85%A8%E6%A0%88/go-backend-demo) | `main.go`<br/>端口: `8081` | SQLite 文件<br/>(`gorm_demo.db`) | [📘 Go 从零搭建到部署全流程指南.md](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/AI%E5%85%A8%E6%A0%88/Go%E5%90%8E%E7%AB%AF%E4%BB%8E%E9%9B%B6%E6%90%AD%E5%BB%BA%E5%88%B0%E9%83%A8%E7%BD%B2%E5%85%A8%E6%B5%81%E7%A8%8B%E6%8C%87%E5%8D%97.md) |

---

## 🚀 快速启动命令对比

所有项目均集成了 **CORS 跨域允许** 与 **自动装载初始测试数据** 功能，支持前端直接发起请求！

```bash
# === 1. 启动 Java Spring Boot (端口 8080) ===
cd "f:\project\AI应用开发\AI appointment develop\AI全栈\java-backend-demo"
mvn spring-boot:run

# === 2. 启动 Python FastAPI (端口 8000) ===
cd "f:\project\AI应用开发\AI appointment develop\AI全栈\python-backend-demo"
python main.py

# === 3. 启动 Go Gin (端口 8081) ===
cd "f:\project\AI应用开发\AI appointment develop\AI全栈\go-backend-demo"
$env:GO111MODULE="on"; $env:GOPROXY="https://goproxy.cn,direct"
go run main.go
```
