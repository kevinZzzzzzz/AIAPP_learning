package com.example.demo.controller;

import com.example.demo.common.Result;
import com.example.demo.entity.Appointment;
import com.example.demo.repository.AppointmentRepository;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 预约业务接口控制器 (Controller)
 * 对应前端接口根地址: /api/appointments
 */
@RestController
@RequestMapping("/api/appointments")
public class AppointmentController {

    @Autowired
    private AppointmentRepository appointmentRepository;

    /**
     * GET /api/appointments - 获取所有预约列表 (支持 userId 过滤)
     * 前端: axios.get('/api/appointments') 或 axios.get('/api/appointments?userId=1')
     */
    @GetMapping
    public Result<List<Appointment>> getAppointments(@RequestParam(value = "userId", required = false) Long userId) {
        if (userId != null) {
            return Result.success(appointmentRepository.findByUserId(userId));
        }
        return Result.success(appointmentRepository.findAll());
    }

    /**
     * POST /api/appointments - 创建新预约
     * 前端: axios.post('/api/appointments', { userId: 2, title: "AI Agent 项目咨询", description: "关于大模型应用落地" })
     */
    @PostMapping
    public Result<Appointment> createAppointment(@RequestBody Appointment appointment) {
        if (appointment.getAppointmentTime() == null) {
            appointment.setAppointmentTime(LocalDateTime.now().plusDays(1)); // 默认预约明天
        }
        Appointment saved = appointmentRepository.save(appointment);
        return Result.success("预约创建成功", saved);
    }

    /**
     * DELETE /api/appointments/{id} - 取消/删除预约
     * 前端: axios.delete('/api/appointments/1')
     */
    @DeleteMapping("/{id}")
    public Result<String> deleteAppointment(@PathVariable("id") Long id) {
        appointmentRepository.deleteById(id);
        return Result.success("成功取消/删除预约 ID=" + id, null);
    }

    @PostConstruct
    public void initData() {
        if (appointmentRepository.count() == 0) {
            appointmentRepository.save(new Appointment(2L, "AI 全栈架构实战咨询", "探讨前端如何快速接入 Python / Java 大模型后端", "CONFIRMED", LocalDateTime.now().plusHours(2)));
            appointmentRepository.save(new Appointment(3L, "FastAPI / Spring Boot 接口联调", "前后端数据对接与跨域调试联调", "PENDING", LocalDateTime.now().plusDays(2)));
            System.out.println("🌱 初始化默认预约测试数据成功 (2条)");
        }
    }
}
