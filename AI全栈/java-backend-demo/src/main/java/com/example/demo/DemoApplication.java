package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Spring Boot 应用启动入口类
 */
@SpringBootApplication
public class DemoApplication {

    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
        System.out.println("==================================================");
        System.out.println("🚀 Java 后端应用启动成功！");
        System.out.println("端口: 8080");
        System.out.println("基础接口: http://localhost:8080/api/users");
        System.out.println("H2 数据库控制台: http://localhost:8080/h2-console");
        System.out.println("==================================================");
    }
}
