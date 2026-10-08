package com.example.demo.service.impl;

import com.example.demo.entity.User;
import com.example.demo.repository.UserRepository;
import com.example.demo.service.UserService;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 用户业务逻辑实现类
 */
@Service
public class UserServiceImpl implements UserService {

    @Autowired
    private UserRepository userRepository;

    @Override
    public List<User> getAllUsers() {
        return userRepository.findAll();
    }

    @Override
    public User getUserById(Long id) {
        return userRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("找不到 ID=" + id + " 的用户"));
    }

    @Override
    public User createUser(User user) {
        return userRepository.save(user);
    }

    @Override
    public User updateUser(Long id, User userDetails) {
        User existingUser = getUserById(id);
        if (userDetails.getNickname() != null) {
            existingUser.setNickname(userDetails.getNickname());
        }
        if (userDetails.getRole() != null) {
            existingUser.setRole(userDetails.getRole());
        }
        return userRepository.save(existingUser);
    }

    @Override
    public void deleteUser(Long id) {
        userRepository.deleteById(id);
    }

    @Override
    @PostConstruct
    public void initDefaultData() {
        if (userRepository.count() == 0) {
            userRepository.save(new User("admin", "全栈超级管理员", "ADMIN"));
            userRepository.save(new User("kevin", "前端开发工程师", "USER"));
            userRepository.save(new User("alice", "AI 算法工程师", "USER"));
            System.out.println("🌱 初始化默认测试用户成功 (3条)");
        }
    }
}
