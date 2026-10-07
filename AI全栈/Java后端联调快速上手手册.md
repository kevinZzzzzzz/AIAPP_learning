我无法直接向你的本地磁盘写入文件，但我已经整理好完整的 Markdown 文档内容。你可以在指定路径 `/Users/kevinzzzzzz/Documents/Code/AIAPP_learning/AI全栈` 下新建一个 `.md` 文件（推荐命名：`Java后端联调快速上手手册.md`），将下面的内容完整粘贴保存即可。

---

# 前端工程师 Java 后端快速看懂与联调手册

> 
> 定位：**看懂代码、梳理接口、联调排错**，不追求精通Java开发；适配前端开发背景，大量对比 Node/JS 概念降低理解门槛
> 目标达成周期：碎片时间 1~2 周，达到能独立梳理 Java 项目接口、看懂数据库逻辑、完成前后端联调排错

---

## 一、前置：先划清学习边界

### ✅ 必须掌握

1. 看懂 SpringBoot 项目结构，快速定位接口定义
2. 看懂接口的请求方式、路径、入参字段、出参结构
3. 看懂基础 SQL 与数据库表结构，理解数据流向
4. 能用 Postman/APIFox 独立调用 Java 后端接口
5. 排查联调常见问题（400/404/500/跨域/参数不匹配）

### ❌ 现阶段不用深入

- JVM 原理、多线程、并发编程
- Spring 底层源码、Bean 生命周期
- 复杂设计模式、微服务架构细节
- 手写复杂 SQL、数据库索引优化

---

## 二、Java 基础：够用版（只学看懂代码需要的部分）

### 2.1 基础语法快速对应（对比 JS）

| 概念 | Java 示例 | JS/TS 对应 | 说明 |
| --- | --- | --- | --- |
| 变量定义 | `String name = "test";` | `const name = "test";` | Java 是强类型，必须声明类型 |
| 函数/方法 | `public User getUserById(Long id) { ... }` | `function getUserById(id) { ... }` | 方法必须声明返回值类型、参数类型 |
| 类 | `public class User { ... }` | `class User { ... }` | Java 所有代码基本都写在类里 |
| 对象实例化 | `User u = new User();` | `const u = new User();` | 用法一致 |
| 数组/列表 | `List<String> list = new ArrayList<>();` | `const list = [];` | Java 用集合类对应 JS 数组 |
| 空值 | `null` | `null / undefined` | Java 只有 null |

> 
> 核心认知：Java 代码 = 类 + 方法 + 注解。看懂注解 = 看懂 80% 的 SpringBoot 接口逻辑。

### 2.2 最核心：Spring 注解（看懂接口的钥匙）

注解是写在方法/类上面、以 `@` 开头的标记，SpringBoot 靠注解定义路由、参数、组件等，对应 Node 里的路由装饰器、中间件配置。

必须认识的核心注解：

- `@RestController`：标记这个类是接口控制器（对应 Express 的路由模块），所有方法返回 JSON
- `@RequestMapping("/api/xxx")`：定义接口根路径
- `@GetMapping / @PostMapping / @PutMapping / @DeleteMapping`：定义请求方式和子路径
- `@RequestParam`：接收 URL 查询参数（对应 `?id=1`）
- `@PathVariable`：接收路径参数（对应 `/user/{id}`）
- `@RequestBody`：接收请求体 JSON 参数
- `@Service`：标记业务逻辑类
- `@Mapper`：标记数据库操作类
- `@Autowired`：依赖注入（相当于自动实例化对象，不用自己 new）

### 2.3 常用数据类型对照

| Java 类型 | JS/TS 对应 | 常见场景 |
| --- | --- | --- |
| `String` | `string` | 字符串、文本 |
| `Integer / Long` | `number` | 整数、ID；Long 是长整数 |
| `Double / BigDecimal` | `number` | 小数、金额 |
| `Boolean` | `boolean` | 布尔值 |
| `Date / LocalDateTime` | `Date` | 日期时间 |
| `List<T>` | `T[]` | 数组/列表 |
| `Map<K,V>` | `Record<K,V>` | 键值对对象 |

### 2.4 看懂类与方法的结构

```
// 类定义
public class UserController {
    // 注入依赖（自动创建对象，不用手动 new）
    @Autowired
    private UserService userService;

    // 方法定义：访问修饰符 + 返回值类型 + 方法名(参数)
    public UserDTO getUserById(Long id) {
        // 调用业务层方法
        return userService.getById(id);
    }
}
```

- 访问修饰符 `public`：公开可调用，接口方法基本都是 public
- 返回值类型：方法执行完返回的数据类型，`void` 表示无返回值

---

## 三、Java 后端项目标准结构（SpringBoot + Maven）

### 3.1 标准目录结构

```
项目根目录
├── src
│   ├── main
│   │   ├── java
│   │   │   └── com.xxx.项目名
│   │   │       ├── controller      # 接口层（联调核心）
│   │   │       ├── service         # 业务逻辑层
│   │   │       ├── mapper/dao      # 数据库操作层
│   │   │       ├── entity/domain   # 数据库实体类（对应表）
│   │   │       ├── dto/vo          # 数据传输对象（前后端交互）
│   │   │       ├── config          # 配置类（跨域、拦截器等）
│   │   │       └── common          # 公共工具、常量、统一返回类
│   │   └── resources
│   │       ├── application.yml     # 主配置文件（数据库、端口等）
│   │       └── mapper              # MyBatis XML 映射文件
│   └── test                        # 单元测试
├── pom.xml                         # Maven 依赖配置（对应 package.json）
└── Dockerfile                      # 容器部署配置
```

### 3.2 各层职责与 Node/前端对应

| 层级 | 职责 | Node/前端对应概念 | 你需要关注程度 |
| --- | --- | --- | --- |
| **controller 控制层** | 接收前端请求、参数校验、调用 service、返回结果 | Express/Nest 的路由层（router） | ⭐⭐⭐⭐⭐ 最高 |
| **service 业务层** | 处理业务逻辑、事务控制、组合多个 mapper 操作 | Node 业务逻辑层（service） | ⭐⭐⭐ 看懂流程 |
| **mapper 数据层** | 直接操作数据库，写 SQL | Node 里的数据库模型层（model/dao） | ⭐⭐⭐ 看懂 SQL |
| **entity 实体类** | 和数据库表一一对应的类 | 数据库表结构定义 | ⭐⭐⭐ 看懂字段 |
| **dto/vo 传输对象** | 接口入参/出参的数据结构 | TS 的 interface 类型定义 | ⭐⭐⭐⭐⭐ 最高 |
| config 配置层 | 跨域、拦截器、全局异常等配置 | Node 中间件、插件配置 | ⭐⭐ 出问题时看 |

> 
> 关键结论：联调阶段 90% 的时间只需要看 **controller + dto + 配置文件**，其他层按需深入。

---

## 四、快速看懂接口（联调核心能力）

### 4.1 三步定位一个接口

1. 全局搜索 `@RestController`，找到所有接口类
2. 看类上的 `@RequestMapping` 得到根路径
3. 看方法上的 `@GetMapping/@PostMapping` 得到子路径和请求方式

### 4.2 接口定义示例详解

```
@RestController                 // 标记这是接口控制器，返回JSON
@RequestMapping("/api/user")    // 接口根路径：/api/user
public class UserController {

    @Autowired
    private UserService userService;

    // 接口1：GET /api/user/123
    @GetMapping("/{id}")
    public Result<UserVO> getUserById(@PathVariable Long id) {
        return Result.success(userService.getById(id));
    }

    // 接口2：POST /api/user/list
    @PostMapping("/list")
    public Result<PageVO<UserVO>> listUser(@RequestBody UserQueryDTO query) {
        return Result.success(userService.list(query));
    }
}
```

### 4.3 三种参数接收方式

| 注解 | 对应请求形式 | 示例 |
| --- | --- | --- |
| `@PathVariable` | 路径参数 | `GET /api/user/123` → id = 123 |
| `@RequestParam` | URL 查询参数 | `GET /api/user?name=张三&page=1` |
| `@RequestBody` | 请求体 JSON | POST/PUT 请求的 JSON  body |

### 4.4 看懂入参/出参结构（DTO/VO）

DTO 就是接口的入参类型，VO 是出参类型，等同于 TS 的 interface。

```
// 入参 DTO
public class UserQueryDTO {
    private String name;      // 用户名（可选）
    private Integer pageNum;  // 页码
    private Integer pageSize; // 每页条数
}

// 出参 VO
public class UserVO {
    private Long id;
    private String name;
    private String email;
    private LocalDateTime createTime;
}
```

> 
> 技巧：看 DTO 字段就能知道接口要传什么、返回什么，不用猜字段名。

### 4.5 统一返回格式

绝大多数 Java 项目会封装统一返回类 `Result`，结构固定：

```
{
  "code": 200,
  "msg": "success",
  "data": {}
}
```

对应前端响应拦截器里的统一格式处理。

---

## 五、看懂数据库逻辑与 SQL

### 5.1 找到数据库配置

在 `resources/application.yml` 中：

```
server:
  port: 8080          # 服务端口

spring:
  datasource:
    url: jdbc:mysql://localhost:3306/数据库名
    username: root
    password: 123456
    driver-class-name: com.mysql.cj.jdbc.Driver
```

拿到地址、账号、库名，就可以用数据库工具连接查看表结构。

### 5.2 看懂表结构（Entity 实体类）

实体类和数据库表一一对应，字段对应表的列。

```
@TableName("user")        // 对应数据库表名 user
public class User {
    @TableId(type = AUTO)
    private Long id;       // 主键ID
    private String name;   // 用户名
    private String email;  // 邮箱
    private Integer status;
    private LocalDateTime createTime;
}
```

> 
> 规律：类名 = 表名驼峰，字段名 = 列名驼峰。`user_name` 字段对应 Java 字段 `userName`。

### 5.3 看懂数据库操作（MyBatis）

Java 最常用的数据库框架是 MyBatis，有两种写法：

1. **注解版**：直接在 mapper 方法上写 SQL

```
@Mapper
public interface UserMapper {
    @Select("SELECT * FROM user WHERE id = #{id}")
    User selectById(Long id);
}
```

2. **XML 版**：SQL 写在 `resources/mapper/*.xml` 里，和 mapper 接口对应

```
<select id="selectById" resultType="User">
    SELECT * FROM user WHERE id = #{id}
</select>
```

> 
> 你只需要：找到 SQL，看懂语句含义，知道数据从哪张表、什么条件查出来。

### 5.4 基础 SQL 快速读懂

| 语句 | 作用 | 重点看什么 |
| --- | --- | --- |
| `SELECT ... FROM 表 WHERE 条件` | 查询 | 查哪些字段、哪张表、过滤条件 |
| `INSERT INTO 表 (...) VALUES (...)` | 新增 | 插入哪些字段 |
| `UPDATE 表 SET ... WHERE ...` | 更新 | 修改哪些字段、条件 |
| `DELETE FROM 表 WHERE ...` | 删除 | 删除条件 |
| `LEFT JOIN 表2 ON ...` | 联表查询 | 关联哪张表、关联字段 |
| `LIMIT offset, size` | 分页 | 分页逻辑 |

---

## 六、Java 服务部署与运行

### 6.1 本地运行与 Jar 包

SpringBoot 内置了 Tomcat 服务器，不用单独装，对应 Node 直接 `node server.js`。

- 本地启动：IDE 里点启动，或执行 `mvn spring-boot:run`
- 打包：`mvn package` 生成 `target/xxx.jar`
- 运行 jar：`java -jar xxx.jar`

### 6.2 Docker 部署

项目根目录一般有 `Dockerfile`，构建镜像后运行容器，和前端 Docker 部署逻辑一致。

```
FROM openjdk:17
COPY target/xxx.jar app.jar
ENTRYPOINT ["java", "-jar", "/app.jar"]
```

### 6.3 Nginx 反向代理

和前端部署的 Nginx 逻辑一样，把 `/api` 请求转发到后端服务端口。

```
location /api/ {
    proxy_pass [http://localhost:8080/](http://localhost:8080/);
}
```

### 6.4 多环境配置

通过 `application-dev.yml`、`application-test.yml`、`application-prod.yml` 区分环境，在主配置里指定激活哪个环境，对应前端的 `.env.development`、`.env.production`。

---

## 七、前后端联调完整实操步骤

### 7.1 拿到项目后的梳理流程

1. **看配置**：打开 `application.yml`，确认服务端口、数据库地址
2. **找接口**：全局搜索 `@RestController`，列出所有 controller 和根路径
3. **列清单**：整理每个接口的请求方式、完整路径、入参 DTO、出参结构
4. **看字段**：打开入参/出参 DTO 类，确认字段名和类型
5. **测接口**：用 Postman/APIFox 先调用通，再对接前端

### 7.2 接口测试要点

- GET 请求：参数拼在 URL 后面，对应 `@RequestParam`
- POST 请求：Body 选 raw → JSON，对应 `@RequestBody`
- 带 token：在 Headers 里加 `Authorization: Bearer xxx`
- 路径参数：把 `{id}` 替换成实际值

### 7.3 常见联调报错排查

| 报错 | 常见原因 | 排查方向 |
| --- | --- | --- |
| 400 Bad Request | 参数类型错误、缺必填字段、格式不对 | 对照 DTO 检查字段名、类型、是否必填 |
| 404 Not Found | 路径写错、服务没启动、上下文路径不对 | 核对完整 URL、确认服务端口是否正确 |
| 401/403 | 未登录、权限不足 | 检查 token 是否携带、是否过期 |
| 500 Internal Server Error | 后端代码报错、数据库异常 | 看后端控制台异常堆栈，关键字搜 `Caused by` |
| 跨域 CORS 错误 | 后端没配跨域 | 找 config 里的 Cors 配置，或让后端加 |
| 字段名对不上 | 下划线/驼峰不匹配 | Java 驼峰 → 数据库下划线，前端传驼峰即可 |

---

## 八、Java → Node/前端 术语对照表

| Java 术语 | Node/前端对应 | 含义 |
| --- | --- | --- |
| SpringBoot | Express / NestJS | 后端开发框架 |
| Controller | Router / 路由 | 接口入口层 |
| Service | Service / 业务层 | 业务逻辑处理 |
| Mapper / DAO | Model / ORM | 数据库操作层 |
| Entity | 数据库表模型 | 和表一一对应的类 |
| DTO / VO | TS Interface | 前后端传输的数据结构 |
| Bean | 实例对象 | Spring 管理的对象 |
| Maven | npm / pnpm | 依赖管理工具 |
| pom.xml | package.json | 依赖配置文件 |
| Jar 包 | 打包后的 server.js | 可运行的服务包 |
| Tomcat | 类似 Node 运行时 | Web 服务器（SpringBoot 已内置） |

---

## 九、掌握程度自检清单

- 能在项目中快速找到所有 controller 类
- 能说出任意接口的请求方式、完整路径、入参出参字段
- 能看懂 application.yml 中的端口和数据库配置
- 能看懂简单的 SELECT/INSERT/UPDATE SQL
- 能用 Postman 成功调用一个 Java 后端接口
- 能独立排查 400/404/跨域 等常见联调问题

> 
> 达到以上标准，就完全满足「和 Java 后端联调、看懂接口与数据库逻辑」的工作需求，不需要再深入学习 Java 底层开发。