"""
Python 数据库操作全解 —— 原生 SQL 与 ORM 增删改查 (CRUD) 面向前端对比指南
========================================================================
作为前端，你可能用过前端索引数据库 IndexedDB、Node.js 中的 mysql2 / pg 驱动、或者 Prisma / TypeORM。

在 Python 中，数据库操作分为两条主流路线：
1. 【路线 A：原生 sqlite3】—— Python 标准库内置，零安装零依赖！适合快速测试与小型项目。
2. 【路线 B：SQLAlchemy ORM】—— 全栈生产环境标准（对标 JS 的 Prisma / TypeORM），用类和对象操作数据库。

运行方法：python 09_Python数据库操作全解_原生SQL与ORM增删改查.py
"""

import os
import sqlite3
from typing import List, Dict, Any, Optional

# ==============================================================================
# 🎯 路线 A：Python 原生 sqlite3 模块 (无需 pip 安装任何包，开箱即用)
# ==============================================================================

def demo_sqlite3_raw_sql():
    print("\n==================================================")
    print(" 路线 A：原生 sqlite3 模块 (底层 SQL 增删改查)")
    print("==================================================")

    db_filename = "sqlite3_demo.db"
    
    # 1. 建立数据库连接 (如果文件不存在，会自动在本地创建 sqlite3_demo.db)
    # JS: const conn = await mysql.createConnection({...});
    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()  # 获取游道/游标 (Cursor)，用来执行 SQL 语句

    # 2. 建表 (Create Table)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            score REAL DEFAULT 0.0,
            course TEXT
        )
    """)
    conn.commit()
    print("1. 建表成功 (students 表)")

    # -------------------------------------------------------------------------
    # 3. 增 (CREATE / INSERT)
    # 💥 关键点: 推荐使用 ? 占位符进行参数化查询，防止 SQL 注入漏洞！
    # JS: db.query("INSERT INTO students (name, age) VALUES (?, ?)", [name, age])
    # -------------------------------------------------------------------------
    # 插入单条
    cursor.execute(
        "INSERT INTO students (name, age, score, course) VALUES (?, ?, ?, ?)",
        ("Alice", 22, 95.5, "Python全栈")
    )
    # 批量插入多条 (executemany)
    student_list = [
        ("Bob", 25, 88.0, "React前端"),
        ("Charlie", 20, 60.0, "AI Agent"),
        ("David", 28, 72.5, "Python全栈")
    ]
    cursor.executemany(
        "INSERT INTO students (name, age, score, course) VALUES (?, ?, ?, ?)",
        student_list
    )
    conn.commit()  # 💥 必须调用 commit() 提交事务，数据才会真正写入磁盘！
    print("2. 插入 4 条测试数据成功")

    # -------------------------------------------------------------------------
    # 4. 查 (READ / SELECT)
    # -------------------------------------------------------------------------
    # === A. 查全部数据 (.fetchall()) ===
    # JS: const rows = await db.query("SELECT * FROM students");
    cursor.execute("SELECT id, name, age, score, course FROM students")
    all_rows = cursor.fetchall()
    print("\n--- 4.1 查询全表数据 (fetchall) ---")
    for row in all_rows:
        # row 是一个元组 Tuple: (id, name, age, score, course)
        print(f"  ID:{row[0]} | 姓名:{row[1]} | 年龄:{row[2]} | 成绩:{row[3]} | 课程:{row[4]}")

    # === B. 带条件筛选查询与模糊搜索 ===
    # 查找年龄 > 21 且课程为 Python全栈 的学生
    cursor.execute(
        "SELECT name, score FROM students WHERE age > ? AND course = ?",
        (21, "Python全栈")
    )
    filtered_rows = cursor.fetchall()
    print(f"\n--- 4.2 条件筛选 (age > 21 & Python全栈): {filtered_rows}")

    # === C. 查询单条 (.fetchone()) ===
    # JS: const user = await db.query("SELECT * FROM students WHERE id = 1")[0];
    cursor.execute("SELECT * FROM students WHERE name = ?", ("Alice",))
    single_row = cursor.fetchone()
    print(f"--- 4.3 单条查找 (fetchone - Alice): {single_row}")

    # -------------------------------------------------------------------------
    # 5. 改 (UPDATE)
    # -------------------------------------------------------------------------
    # 将 Charlie 的成绩修改为 85.0
    # JS: await db.query("UPDATE students SET score = ? WHERE name = ?", [85.0, "Charlie"]);
    cursor.execute(
        "UPDATE students SET score = ? WHERE name = ?",
        (85.0, "Charlie")
    )
    conn.commit()
    print(f"\n5. 更新成功 (修改受影响行数: {cursor.rowcount})")

    # -------------------------------------------------------------------------
    # 6. 删 (DELETE)
    # -------------------------------------------------------------------------
    # 删除姓名为 Bob 的记录
    cursor.execute("DELETE FROM students WHERE name = ?", ("Bob",))
    conn.commit()
    print(f"6. 删除 Bob 记录成功 (受影响行数: {cursor.rowcount})")

    # 验证最终数据
    cursor.execute("SELECT name, score FROM students")
    print("最终剩余学生数据:", cursor.fetchall())

    # 7. 关闭连接
    conn.close()


# ==============================================================================
# 🎯 路线 B：SQLAlchemy ORM 方式 (全栈主流对标 Prisma / TypeORM)
# ==============================================================================

def demo_sqlalchemy_orm():
    print("\n==================================================")
    print(" 路线 B：SQLAlchemy ORM (对象关系映射 增删改查)")
    print("==================================================")

    try:
        from sqlalchemy import create_engine, Column, Integer, String, Float, Text
        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy.orm import sessionmaker
    except ImportError:
        print("⚠️ 未检测到 `sqlalchemy` 库。可以通过 `pip install sqlalchemy` 安装。")
        return

    # 1. 创建 ORM 基类与数据库引擎
    Base = declarative_base()
    engine = create_engine("sqlite:///sqlalchemy_orm_demo.db", echo=False)

    # 2. 定义数据库表模型 (对标 Prisma Schema 或 TypeORM Entity)
    """
    TS TypeORM 类比:
    @Entity()
    class Product {
      @PrimaryGeneratedColumn() id: number;
      @Column() name: string;
      @Column('float') price: number;
    }
    """
    class Product(Base):
        __tablename__ = "products"

        id = Column(Integer, primary_key=True, autoincrement=True)
        name = Column(String(100), nullable=False)
        price = Column(Float, nullable=False)
        category = Column(String(50), default="General")

        def __repr__(self):
            return f"<Product(id={self.id}, name='{self.name}', price={self.price})>"

    # 3. 自动在数据库中创建物理表
    Base.metadata.create_all(engine)

    # 4. 创建 Session 会话工厂 (用于操作数据库)
    Session = sessionmaker(bind=engine)
    session = Session()

    # -------------------------------------------------------------------------
    # 5. ORM 增 (Create)
    # JS (Prisma): await prisma.product.create({ data: { name: "MacBook", price: 9999 } });
    # -------------------------------------------------------------------------
    p1 = Product(name="iPhone 15", price=5999.0, category="Electronics")
    p2 = Product(name="MacBook Pro", price=12999.0, category="Electronics")
    p3 = Product(name="Python 编程书", price=79.0, category="Books")

    session.add_all([p1, p2, p3])
    session.commit()  # 提交到数据库磁盘文件
    print(f"1. ORM 新增商品成功，自动生成的自增 ID -> iPhone ID: {p1.id}, MacBook ID: {p2.id}")

    # -------------------------------------------------------------------------
    # 6. ORM 查 (Read / Query)
    # -------------------------------------------------------------------------
    # === A. 查全部 (all) ===
    # JS: const products = await prisma.product.findMany();
    all_products = session.query(Product).all()
    print(f"\n--- 6.1 查询所有商品 (all): {all_products}")

    # === B. 按主键 ID 查询 (get / first) ===
    # JS: const product = await prisma.product.findUnique({ where: { id: 1 } });
    product_1 = session.query(Product).filter(Product.id == 1).first()
    print(f"--- 6.2 按主键查找 (id=1): {product_1.name} (价格: {product_1.price})")

    # === C. 条件过滤与排序 (filter & order_by) ===
    # JS: await prisma.product.findMany({ where: { price: { gte: 100 } }, orderBy: { price: 'desc' } })
    expensive_products = (
        session.query(Product)
        .filter(Product.price >= 100.0)
        .order_by(Product.price.desc())
        .all()
    )
    print(f"--- 6.3 价格 >= 100 降序排列: {expensive_products}")

    # -------------------------------------------------------------------------
    # 7. ORM 改 (Update)
    # JS: await prisma.product.update({ where: { id: 1 }, data: { price: 5499 } });
    # -------------------------------------------------------------------------
    # 直接修改 Python 对象的属性，然后 commit 即可！(超级直观)
    target_product = session.query(Product).filter(Product.name == "iPhone 15").first()
    if target_product:
        target_product.price = 5499.0  # 降价 500
        session.commit()
        print(f"\n7. ORM 修改价格成功: {target_product.name} 最新价格为 -> {target_product.price}")

    # -------------------------------------------------------------------------
    # 8. ORM 删 (Delete)
    # JS: await prisma.product.delete({ where: { name: "Python 编程书" } });
    # -------------------------------------------------------------------------
    book = session.query(Product).filter(Product.name == "Python 编程书").first()
    if book:
        session.delete(book)
        session.commit()
        print(f"8. ORM 删除商品成功: {book.name}")

    # 最终结果校验
    remaining = session.query(Product).all()
    print(f"数据库最终剩余商品: {remaining}")

    session.close()


if __name__ == "__main__":
    demo_sqlite3_raw_sql()
    demo_sqlalchemy_orm()
