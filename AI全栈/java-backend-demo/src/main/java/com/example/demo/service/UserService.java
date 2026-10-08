package com.example.demo.service;

import com.example.demo.entity.User;
import java.util.List;

/**
 * 用户业务逻辑接口 Service
 */
public interface UserService {
    List<User> getAllUsers();
    User getUserById(Long id);
    User createUser(User user);
    User updateUser(Long id, User userDetails);
    void deleteUser(Long id);
    void initDefaultData();
}
