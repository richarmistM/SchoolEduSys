SchoolEduSys - 学分制教务管理系统📖 项目简介SchoolEduSys 是一个基于 Python Flask 和 MySQL 开发的轻量级教务管理系统。该系统实现了经典的 MVC 架构，提供管理员、教师、学生三种角色的分权管理功能，支持选课冲突检测、成绩自动计算（触发器实现）、多维度统计分析以及动态系统设置等功能。🛠️ 技术栈后端: Python 3.x, Flask数据库: MySQL 8.0+数据库驱动: PyMySQL前端: HTML5, CSS3, Jinja2 模板引擎✨ 核心功能1. 管理员 (Admin)基础数据管理：对院系、教师、学生、课程进行增删改查。开课管理：安排课程的授课教师、上课时间及学期。统计分析：查看各院系学生人数统计。查看课程平均分统计。高级统计：调用存储过程查询指定教师的课程及选课人数。系统设置：动态控制系统开关：是否允许学生退课。是否允许教师修改成绩。2. 教师 (Teacher)课程管理：查看自己教授的课程及学生名单。成绩录入：录入平时成绩和考试成绩（受管理员开关控制）。自动计算：系统根据 30% 平时成绩 + 70% 考试成绩自动计算总评（支持手动触发批量计算）。3. 学生 (Student)选课系统：查看可选课程，支持上课时间冲突检测，防止选课撞车。成绩查询：查看已选课程的详细成绩。学分统计：自动统计已修读及格课程的总学分。退课功能：在管理员开启允许退课期间，可进行退课操作。📂 项目结构PlaintextSchoolEduSys/
├── app.py                  # Flask 主程序（路由、业务逻辑）
├── db_config.py            # 数据库连接配置
├── create_database.py      # (可选) Python 脚本初始化数据库
├── school_init.sql         # 核心数据库初始化脚本 (包含表结构、数据、触发器、存储过程)
├── templates/              # 前端 HTML 模板
│   ├── login.html          # 登录页
│   ├── index.html          # 角色主页
│   ├── student_course.html # 学生选课页
│   ├── teacher_score.html  # 教师成绩页
│   ├── admin_stats.html    # 管理员统计页
│   ├── admin_settings.html # 系统设置页
│   └── admin_*.html        # 其他管理页面
└── README.md               # 项目说明文档
🚀 快速开始1. 环境准备确保已安装 Python 和 MySQL。安装项目依赖：Bashpip install flask pymysql
2. 数据库配置登录 MySQL 数据库。推荐方式：直接使用 school_init.sql 初始化数据库。该脚本会自动创建数据库 school1，并解决中文乱码问题。在 MySQL 命令行执行：SQLsource /path/to/your/school_init.sql;
修改配置：打开 db_config.py，修改 MySQL 连接信息：Pythondef get_db_connection():
    conn = pymysql.connect(
        host='localhost',
        user='root',       # 您的用户名
        password='您的密码', # 您的密码
        database='school1',
        charset='utf8mb4'
    )
    return conn
3. 启动项目在项目根目录下运行：Bashpython app.py
若看到 Running on http://127.0.0.1:5000，则启动成功。4. 访问系统打开浏览器访问 http://127.0.0.1:5000。🔐 默认测试账号系统初始化后包含以下测试数据：角色账号 (User ID)默认密码说明管理员admin123456拥有最高权限教师0101123456姓名：陈迪茂 (计算机学院)学生1102123456姓名：刘晓明 (计算机学院)(注：密码经过 MD5 加密存储，数据库中不可见明文)⚙️ 数据库高级特性说明本项目使用了 MySQL 的高级特性来保证数据完整性和业务逻辑：触发器 (Triggers):trg_calc_total_score: 在插入成绩时，自动计算 总评 = 平时*0.3 + 考试*0.7。trg_update_total_score: 在更新成绩时，重新计算总评。存储过程 (Stored Procedures):sp_get_student_credit: 计算学生已修（及格）总学分。sp_get_teacher_course_student_count: 统计教师的教学工作量。系统设置表:使用 system_settings 表存储 Key-Value 配置，无需重启服务器即可实时改变业务规则（如禁止退课）。⚠️ 注意事项编码问题: 请确保数据库字符集为 utf8mb4，否则中文字符可能乱码。推荐使用项目提供的 school_init.sql 进行初始化。安全性: 当前 app.secret_key 为硬编码，生产环境部署时请修改为随机字符串。选课逻辑: 学生选课时会自动检查上课时间（如“星期一5-8”）是否与已选课程冲突。
