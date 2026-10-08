package com.example.demo.controller;

import com.example.demo.common.Result;
import com.example.demo.entity.User;
import com.example.demo.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 用户接口控制器 (Controller)
 * 对应前端接口根地址: /api/users
 */
@RestController
@RequestMapping("/api/users")
public class UserController {

    @Autowired
    private UserService userService;

    /**
     * GET /api/users - 获取所有用户列表
     * 前端: axios.get('/api/users')
     */
    @GetMapping
    public Result<List<User>> getAllUsers() {
        List<User> users = userService.getAllUsers();
        return Result.success(users);
    }

    /**
     * GET /api/users/{id} - 根据 ID 查询单个用户
     * 前端: axios.get('/api/users/1')
     */
    @GetMapping("/{id}")
    public Result<User> getUserById(@PathVariable("id") Long id) {
        User user = userService.getUserById(id);
        return Result.success(user);
    }

    /**
     * POST /api/users - 创建新用户
     * 前端: axios.post('/api/users', { username: "jack", nickname: "杰克", role: "USER" })
     */
    @PostMapping
    public Result<User> createUser(@RequestBody User user) {
        User createdUser = userService.createUser(user);
        return Result.success("用户创建成功", createdUser);
    }

    /**
     * PUT /api/users/{id} - 更新用户信息
     * 前端: axios.put('/api/users/2', { nickname: "前端全栈高级工程师" })
     */
    @PutMapping("/{id}")
    public Result<User> updateUser(@PathVariable("id") Long id, @RequestBody User userDetails) {
        User updatedUser = userService.updateUser(id, userDetails);
        return Result.success("用户信息更新成功", updatedUser);
    }

    /**
     * DELETE /api/users/{id} - 删除用户
     * 前端: axios.delete('/api/users/3')
     */
    @DeleteMapping("/{id}")
    public Result<String> deleteUser(@PathVariable("id") Long id) {
        userService.deleteUser(id);
        return Result.success("成功删除用户 ID=" + id, null);
    }
}
