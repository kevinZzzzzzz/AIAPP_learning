# 🚀 Java Spring Boot 后端从零搭建、本地运行与服务器部署全流程指南

本文档专门为你（前端开发者）编写，配套目录下的 Java 后端标准示例项目 [**`java-backend-demo`**](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/AI%E5%85%A8%E6%A0%88/java-backend-demo)。

通过本指南，你可以清晰了解**需要准备什么环境、如何安装配置、如何在本地启动调测，以及未来如何打包部署到云服务器**！

---

## 🛠️ 一、 需要什么环境与安装步骤

构建与运行 Java Spring Boot 项目需要以下 3 大核心环境：

### 1. Java 运行与开发环境 (JDK 17)
*   **版本要求**：Java 17 LTS（当前项目采用的最佳长久支持版本，系统经检测已安装 `17.0.15`）。
*   **如何检查与配置环境变量**：
    1. 打开命令行（PowerShell / CMD），输入 `java -version`，能看到 `17.x.x` 即说明正常。
    2. 如果未配置，在系统环境变量中新增 `JAVA_HOME` 指向 JDK 安装目录（如 `C:\Program Files\Java\jdk-17`），并在 `Path` 中追加 `%JAVA_HOME%\bin`。

### 2. 构建工具 Maven (或使用 IDE 内置 Maven)
*   **作用**：相当于前端的 `npm` 或 `yarn`，用来下载 Java 项目的依赖包（Jar 包）并进行编译打包。
*   **安装步骤**：
    1. 访问 [Apache Maven 官网](https://maven.apache.org/download.cgi) 下载 `apache-maven-3.9.x-bin.zip`。
    2. 解压到本地目录（如 `C:\dev\apache-maven-3.9.6`）。
    3. 在系统环境变量 `Path` 中添加 `C:\dev\apache-maven-3.9.6\bin`。
    4. 命令行输入 `mvn -v` 验证安装成功。

### 3. 开发编辑器 (VS Code 或 IntelliJ IDEA)
*   **推荐扩展 (VS Code)**：在扩展商店搜索并安装 **`Extension Pack for Java`**（微软官方出品，安装后可直接在代码上方点击 `Run` 启动服务器）。
*   **推荐 IDE (IntelliJ IDEA)**：Java 开发首选 IDE，下载 Community（社区免费版）或 Ultimate 版即可。

### 4. 数据库 (开箱即用零配置 H2 内存库)
*   **零配置内置库**：项目默认集成了 **H2 数据库**，项目启动时会在内存中自动创建数据库与表，**你不需要在电脑上提前安装 MySQL 软件即可直接运行**！
*   **可选 MySQL**：如果后续想接入真实 MySQL 数据库，仅需在配置文件中切换注释即可（下文有详细教学）。

---

## 📁 二、 项目结构与常规数据内容拆解

为你建立的项目位于 [**`java-backend-demo`**](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/AI%E5%85%A8%E6%A0%88/java-backend-demo)，采用业界规范的四层分层架构：

```
java-backend-demo/
├── pom.xml                                       # 1. 项目说明书 (对标 package.json)
└── src/
    ├── main/
    │   ├── java/com/example/demo/
    │   │   ├── DemoApplication.java              # 2. 项目启动入口类 (main 方法)
    │   │   ├── common/
    │   │   │   └── Result.java                   # 3. 统一前端响应格式封装 { code, message, data }
    │   │   ├── config/
    │   │   │   └── CorsConfig.java               # 4. 全局 CORS 跨域允许配置
    │   │   ├── entity/
    │   │   │   ├── User.java                     # 5. 用户数据表实体
    │   │   │   └── Appointment.java              # 6. 预约业务数据表实体
    │   │   ├── repository/
    │   │   │   ├── UserRepository.java           # 7. 用户数据库 DAO 层 (JPA 零 SQL CRUD)
    │   │   │   └── AppointmentRepository.java    # 8. 预约数据库 DAO 层
    │   │   ├── service/
    │   │   │   ├── UserService.java              # 9. 业务接口定义
    │   │   │   └── impl/UserServiceImpl.java     # 10. 业务逻辑实现与默认种子数据加载
    │   │   └── controller/
    │   │       ├── UserController.java           # 11. 用户 RESTful 接口控制器
    │   │       └── AppointmentController.java    # 12. 预约 RESTful 接口控制器
    │   └── resources/
    │       └── application.yml                   # 13. 核心配置文件 (端口、H2 数据库、日志)
```

---

## 💻 三、 本地如何运行与测试

### 方式 A：在 VS Code / IntelliJ IDEA 中一键运行（推荐 ⭐️）

1. 在 VS Code 中打开文件夹：[**`java-backend-demo`**](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/AI%E5%85%A8%E6%A0%88/java-backend-demo)。
2. 打开启动文件 [`DemoApplication.java`](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/AI%E5%85%A8%E6%A0%88/java-backend-demo/src/main/java/com/example/demo/DemoApplication.java)。
3. 在 `main` 方法上方找到提示的按钮 **▶️ Run** (或在右键菜单中选择 `Run Java`)。
4. 观察下方终端控制台，当打出以下日志时表示启动成功：
   ```
   🚀 Java 后端应用启动成功！
   端口: 8080
   基础接口: http://localhost:8080/api/users
   H2 数据库控制台: http://localhost:8080/h2-console
   ```

### 方式 B：通过命令行运行

```bash
# 1. 切换到项目根目录
cd "f:\project\AI应用开发\AI appointment develop\AI全栈\java-backend-demo"

# 2. 使用 Maven 插件运行
mvn spring-boot:run
```

---

## 🧪 四、 接口测试与可视化数据库查看

### 1. 测试基础 RESTful 接口
启动成功后，你可以直接在浏览器或 Postman 中测试以下预置的真实数据接口：

*   **获取用户列表**：`GET http://localhost:8080/api/users`
    *   **响应结构**：
        ```json
        {
          "code": 200,
          "message": "操作成功",
          "data": [
            { "id": 1, "username": "admin", "nickname": "全栈超级管理员", "role": "ADMIN" },
            { "id": 2, "username": "kevin", "nickname": "前端开发工程师", "role": "USER" },
            { "id": 3, "username": "alice", "nickname": "AI 算法工程师", "role": "USER" }
          ]
        }
        ```
*   **获取预约列表**：`GET http://localhost:8080/api/appointments`
*   **新增预约**：`POST http://localhost:8080/api/appointments`
    *   **请求 Body (JSON)**：
        ```json
        {
          "userId": 2,
          "title": "大模型与 Spring Boot 全栈联调",
          "description": "探讨前端 Axios 如何对接 Java API",
          "status": "PENDING"
        }
        ```

### 2. 浏览器直接看可视化数据库数据 (H2 Console)
1. 保持项目运行，打开浏览器访问：`http://localhost:8080/h2-console`
2. 参数填写：
   *   **JDBC URL**: `jdbc:h2:mem:demo_db`
   *   **User Name**: `sa`
   *   **Password**: (留空不填)
3. 点击 **Connect** 按钮登录，左侧即可看到自动生成的 `SYS_USER` 和 `TB_APPOINTMENT` 表，点击即可在页面上用 SQL 查表看数据！

### 3. 前端代码联调范例 (JS / Axios)
前端代码直接调用后端接口示例：
```javascript
// 前端 fetch / axios 示例
async function fetchUsers() {
  const res = await fetch("http://localhost:8080/api/users");
  const result = await res.json();
  if (result.code === 200) {
    console.log("用户数据:", result.data);
  }
}
```

---

## 🚢 五、 后续打包与服务器部署上线

当你的项目开发完毕，需要部署到云服务器（如阿里云、腾讯云 Ubuntu / CentOS）时，遵循以下部署流程：

### 1. 在本地编译打包成可执行 Jar 包
在本地命令行中执行：
```bash
cd "f:\project\AI应用开发\AI appointment develop\AI全栈\java-backend-demo"
mvn clean package -DskipTests
```
*   执行完成后，会在项目下生成 `target/` 文件夹。
*   打包产物：[**`target/java-backend-demo-1.0.0-SNAPSHOT.jar`**](file:///f:/project/AI%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91/AI%20appointment%20develop/AI%E5%85%A8%E6%A0%88/java-backend-demo/pom.xml)。

### 2. 方式 A：服务器后台进程直接运行 (最快捷)
1. 使用 SCP 或 FTP 工具将 `.jar` 文件上传到服务器目录 `/www/app/`。
2. 在服务器上确保已安装 JDK 17 (`sudo apt install openjdk-17-jdk`)。
3. 后台不间断运行命令：
   ```bash
   nohup java -jar /www/app/java-backend-demo-1.0.0-SNAPSHOT.jar > /www/app/app.log 2>&1 &
   ```
4. 查看运行日志：`tail -f /www/app/app.log`。

### 3. 方式 B：使用 Docker 容器化部署 (推荐 🔥)
在服务器项目目录下新建 `Dockerfile`：

```dockerfile
# 1. 基础镜像
FROM openjdk:17-jdk-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 复制 jar 包到容器中
COPY java-backend-demo-1.0.0-SNAPSHOT.jar app.jar

# 4. 暴露 8080 端口
EXPOSE 8080

# 5. 启动指令
ENTRYPOINT ["java", "-jar", "app.jar"]
```

运行 Docker 构建与启动指令：
```bash
# 构建镜像
docker build -t java-backend-demo:1.0 .

# 启动容器
docker run -d -p 8080:8080 --name java-backend java-backend-demo:1.0
```

### 4. Nginx 反向代理配置
在 Nginx 配置文件 `/etc/nginx/sites-available/default` 中加入域名或 IP 反向代理：
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 代理 Java 后端接口
    location /api/ {
        proxy_pass http://127.0.0.1:8080/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🎯 总结

通过本示例项目与指南，你已经拥有了一个**标准的、开箱即用的 Java 全栈后端骨架**。
你可以随意在此骨架上修改实体类、扩展 Controller 接口，享受与前端联调的乐趣！
