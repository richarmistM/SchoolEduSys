from flask import Flask, render_template, request, redirect, url_for, session
from db_config import get_db_connection
import pymysql

app = Flask(__name__)
app.secret_key = 'school_edu_sys_2025'  # session加密密钥（必填）


# ---------------------- 通用路由 ----------------------
@app.route('/')
def index():
    """默认跳转登录页"""
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录（权限验证）"""
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')

        # 连接数据库验证
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT role FROM user_role WHERE user_id=%s AND password=MD5(%s)"
        cursor.execute(sql, (user_id, password))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            session['user_id'] = user_id
            session['role'] = result[0]
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='账号或密码错误')

    return render_template('login.html')


@app.route('/home')
def home():
    """角色首页（根据权限展示功能）"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html',
                           user_id=session['user_id'],
                           role=session['role'])


@app.route('/logout')
def logout():
    """退出登录"""
    session.clear()
    return redirect(url_for('login'))


# ---------------------- 学生功能 ----------------------
@app.route('/student/course', methods=['GET', 'POST'])
def student_course():
    """学生选课 + 成绩查询"""
    if session.get('role') != 'student':
        return redirect(url_for('home'))

    student_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # 检查是否允许退课
    cursor.execute("SELECT value FROM system_settings WHERE setting_key = 'allow_course_drop' LIMIT 1")
    setting = cursor.fetchone()
    allow_drop = setting['value'] == '1' if setting else False

    # 1. 查询可选课程（未选过的开课课程）
    sql_optional = """
    SELECT c.semester, c.course_id, co.course_name, c.staff_id, t.name as teacher_name, c.class_time
    FROM class c
    JOIN course co ON c.course_id = co.course_id
    JOIN teacher t ON c.staff_id = t.staff_id
    WHERE (c.semester, c.course_id, c.staff_id) NOT IN (
        SELECT semester, course_id, staff_id FROM course_selection WHERE student_id=%s
    )
    """
    cursor.execute(sql_optional, (student_id,))
    optional_courses = cursor.fetchall()

    # 2. 查询已选课程及成绩（包含class_time信息）
    sql_selected = """
    SELECT cs.semester, cs.course_id, co.course_name, cs.staff_id, t.name as teacher_name,
           cs.normal_score, cs.test_score, cs.total_score, c.class_time
    FROM course_selection cs
    JOIN course co ON cs.course_id = co.course_id
    JOIN teacher t ON cs.staff_id = t.staff_id
    JOIN class c ON cs.semester = c.semester AND cs.course_id = c.course_id AND cs.staff_id = c.staff_id
    WHERE cs.student_id=%s
    """
    cursor.execute(sql_selected, (student_id,))
    selected_courses = cursor.fetchall()

    # 3. 按学期组织已选课程数据
    courses_by_semester = {}
    for course in selected_courses:
        semester = course['semester']
        if semester not in courses_by_semester:
            courses_by_semester[semester] = []
        courses_by_semester[semester].append(course)

    # 获取所有学期列表用于下拉框
    semesters = list(courses_by_semester.keys())
    semesters.sort(reverse=True)  # 按学期倒序排列（最新的学期在前）

    # 4. 选课或退课操作（POST请求）
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            semester = request.form.get('semester')
            course_id = request.form.get('course_id')
            staff_id = request.form.get('staff_id')
            
            # 检查时间冲突
            cursor.execute("""
                SELECT c.class_time, co.course_name, t.name as teacher_name
                FROM course_selection cs
                JOIN class c ON cs.semester = c.semester AND cs.course_id = c.course_id AND cs.staff_id = c.staff_id
                JOIN course co ON c.course_id = co.course_id
                JOIN teacher t ON c.staff_id = t.staff_id
                WHERE cs.student_id = %s AND cs.semester = %s
                """, (student_id, semester))
            scheduled_courses = cursor.fetchall()
            
            # 获取新选课程的时间
            cursor.execute("""
                SELECT class_time
                FROM class
                WHERE semester = %s AND course_id = %s AND staff_id = %s
                """, (semester, course_id, staff_id))
            new_course = cursor.fetchone()
            
            time_conflict = None
            if new_course and new_course['class_time']:
                new_time = new_course['class_time']
                for scheduled in scheduled_courses:
                    if scheduled['class_time'] == new_time:
                        time_conflict = {
                            'new_course_time': new_time,
                            'conflict_course_name': scheduled['course_name'],
                            'conflict_teacher_name': scheduled['teacher_name']
                        }
                        break
            
            if time_conflict:
                error = f"时间冲突：课程时间'{time_conflict['new_course_time']}'与已选课程'{time_conflict['conflict_course_name']}'冲突"
                # 重新获取数据以显示错误信息
                cursor.execute(sql_optional, (student_id,))
                optional_courses = cursor.fetchall()
                cursor.execute(sql_selected, (student_id,))
                selected_courses = cursor.fetchall()
                
                # 按学期重新组织数据
                courses_by_semester = {}
                for course in selected_courses:
                    semester = course['semester']
                    if semester not in courses_by_semester:
                        courses_by_semester[semester] = []
                    courses_by_semester[semester].append(course)
                
                # 获取学期列表
                semesters = list(courses_by_semester.keys())
                semesters.sort(reverse=True)
                
                cursor.close()
                conn.close()
                return render_template('student_course.html',
                                       optional_courses=optional_courses,
                                       selected_courses=selected_courses,
                                       courses_by_semester=courses_by_semester,
                                       semesters=semesters,
                                       allow_drop=allow_drop,
                                       error=error)
            
            try:
                sql_insert = """
                INSERT INTO course_selection (student_id, semester, course_id, staff_id)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql_insert, (student_id, semester, course_id, staff_id))
                conn.commit()
                return redirect(url_for('student_course'))
            except:
                conn.rollback()
        elif action == 'drop' and allow_drop:
            semester = request.form.get('semester')
            course_id = request.form.get('course_id')
            staff_id = request.form.get('staff_id')
            try:
                sql_delete = """
                DELETE FROM course_selection
                WHERE student_id=%s AND semester=%s AND course_id=%s AND staff_id=%s
                """
                cursor.execute(sql_delete, (student_id, semester, course_id, staff_id))
                conn.commit()
                return redirect(url_for('student_course'))
            except:
                conn.rollback()

    # 5. 调用存储过程：查询总学分（修复None值和结果集获取问题）
    cursor.callproc('sp_get_student_credit', (student_id, 0))
    # 跳过存储过程执行状态集，获取有效结果
    cursor.nextset()
    # 获取结果并安全处理None值
    credit_result = cursor.fetchone()
    total_credit = credit_result['p_total_credit'] if (credit_result and credit_result['p_total_credit']) else 0

    cursor.close()
    conn.close()
    return render_template('student_course.html',
                           optional_courses=optional_courses,
                           selected_courses=selected_courses,
                           courses_by_semester=courses_by_semester,
                           semesters=semesters,
                           total_credit=total_credit,
                           allow_drop=allow_drop)

# ---------------------- 教师功能 ----------------------
@app.route('/teacher/score', methods=['GET', 'POST'])
def teacher_score():
    """教师成绩录入"""
    if session.get('role') != 'teacher':
        return redirect(url_for('home'))

    staff_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # 查询教师所授课程
    sql_courses = """
    SELECT DISTINCT c.course_id, co.course_name, c.semester
    FROM class c
    JOIN course co ON c.course_id = co.course_id
    WHERE c.staff_id=%s
    """
    cursor.execute(sql_courses, (staff_id,))
    courses = cursor.fetchall()

    # 获取当前编辑的课程
    current_course_id = request.args.get('course_id')
    current_semester = request.args.get('semester')

    # 如果没有指定课程，默认选择第一个课程
    if current_course_id and current_semester:
        selected_course = {'course_id': current_course_id, 'semester': current_semester}
    elif courses:
        selected_course = {'course_id': courses[0]['course_id'], 'semester': courses[0]['semester']}
    else:
        selected_course = None

    # 查询当前课程的学生列表
    if selected_course:
        sql_students = """
        SELECT cs.student_id, s.name as student_name, cs.semester, cs.course_id, co.course_name,
               cs.normal_score, cs.test_score, cs.total_score
        FROM course_selection cs
        JOIN student s ON cs.student_id = s.student_id
        JOIN course co ON cs.course_id = co.course_id
        WHERE cs.staff_id=%s AND cs.course_id=%s AND cs.semester=%s
        ORDER BY s.student_id
        """
        cursor.execute(sql_students, (staff_id, selected_course['course_id'], selected_course['semester']))
        students = cursor.fetchall()
    else:
        students = []

    # 检查是否允许教师修改成绩
    cursor.execute("SELECT value FROM system_settings WHERE setting_key = 'allow_teacher_modify_scores' LIMIT 1")
    setting = cursor.fetchone()
    allow_teacher_modify_scores = setting['value'] == '1' if setting else False

    # 处理成绩录入或手动计算总评成绩（POST请求）
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_scores' and allow_teacher_modify_scores:
            student_id = request.form.get('student_id')
            semester = request.form.get('semester')
            course_id = request.form.get('course_id')
            normal_score = request.form.get('normal_score')
            test_score = request.form.get('test_score')

            # 空值处理
            normal_score = normal_score if normal_score != '' else None
            test_score = test_score if test_score != '' else None

            try:
                # 更新成绩，总评成绩将由触发器自动计算
                sql_update = """
                UPDATE course_selection 
                SET normal_score=%s, test_score=%s
                WHERE student_id=%s AND semester=%s AND course_id=%s AND staff_id=%s
                """
                cursor.execute(sql_update, (normal_score, test_score, student_id, semester, course_id, staff_id))
                conn.commit()
                # 重定向以刷新数据
                redirect_url = url_for('teacher_score', 
                                      course_id=selected_course['course_id'] if selected_course else None,
                                      semester=selected_course['semester'] if selected_course else None)
                return redirect(redirect_url)
            except Exception as e:
                conn.rollback()
                error = str(e)
                cursor.close()
                conn.close()
                return render_template('teacher_score.html', 
                                       students=students, 
                                       courses=courses, 
                                       selected_course=selected_course,
                                       allow_teacher_modify_scores=allow_teacher_modify_scores,
                                       error=error)
        
        elif action == 'calculate_totals' and allow_teacher_modify_scores:
            # 手动计算当前课程所有学生的总评成绩
            try:
                # 使用固定比例30%和70%计算总评成绩
                sql_update_totals = """
                UPDATE course_selection 
                SET total_score = CASE 
                    WHEN normal_score IS NOT NULL AND test_score IS NOT NULL 
                    THEN ROUND(normal_score * 0.3 + test_score * 0.7)
                    ELSE NULL
                END
                WHERE staff_id=%s AND course_id=%s AND semester=%s
                AND normal_score IS NOT NULL AND test_score IS NOT NULL
                """
                cursor.execute(sql_update_totals, (staff_id, selected_course['course_id'], selected_course['semester']))
                conn.commit()
                
                # 重定向以刷新数据
                redirect_url = url_for('teacher_score', 
                                      course_id=selected_course['course_id'],
                                      semester=selected_course['semester'])
                return redirect(redirect_url)
            except Exception as e:
                conn.rollback()
                error = str(e)
                cursor.close()
                conn.close()
                return render_template('teacher_score.html', 
                                       students=students, 
                                       courses=courses, 
                                       selected_course=selected_course,
                                       allow_teacher_modify_scores=allow_teacher_modify_scores,
                                       error=error)

    cursor.close()
    conn.close()
    return render_template('teacher_score.html', 
                           students=students, 
                           courses=courses, 
                           selected_course=selected_course,
                           allow_teacher_modify_scores=allow_teacher_modify_scores)


# ---------------------- 管理员功能 ----------------------
@app.route('/admin/stats')
def admin_stats():
    """管理员统计分析"""
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # 1. 各院系学生人数统计
    sql_dept_student = """
    SELECT d.dept_name, COUNT(s.student_id) as student_count
    FROM department d
    LEFT JOIN student s ON d.dept_id = s.dept_id
    GROUP BY d.dept_name
    """
    cursor.execute(sql_dept_student)
    dept_student_stats = cursor.fetchall()

    # 2. 各课程平均成绩统计
    sql_course_score = """
    SELECT co.course_name, AVG(cs.total_score) as avg_score
    FROM course co
    JOIN course_selection cs ON co.course_id = cs.course_id
    WHERE cs.total_score IS NOT NULL
    GROUP BY co.course_name
    """
    cursor.execute(sql_course_score)
    course_score_stats = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('admin_stats.html',
                           dept_student_stats=dept_student_stats,
                           course_score_stats=course_score_stats)


@app.route('/admin/students', methods=['GET', 'POST'])
def admin_manage_students():
    """管理员管理学生功能"""
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            student_id = request.form.get('student_id')
            name = request.form.get('name')
            sex = request.form.get('sex')
            date_of_birth = request.form.get('date_of_birth')
            native_place = request.form.get('native_place')
            mobile_phone = request.form.get('mobile_phone')
            dept_id = request.form.get('dept_id')
            user_id = request.form.get('user_id', student_id)  # 如果未指定用户ID，则使用学号
            password = request.form.get('password', '123456')  # 如果未指定密码，则使用默认密码

            try:
                sql_insert = """
                INSERT INTO student (student_id, name, sex, date_of_birth, native_place, mobile_phone, dept_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql_insert, (student_id, name, sex, date_of_birth, native_place, mobile_phone, dept_id))
                # 同时在user_role表中添加学生账号
                sql_insert_user = """
                INSERT INTO user_role (user_id, role, password)
                VALUES (%s, 'student', MD5(%s))
                """
                cursor.execute(sql_insert_user, (user_id, password))
                conn.commit()
            except Exception as e:
                conn.rollback()
                error = str(e)
                return render_template('admin_manage_students.html', error=error)

        elif action == 'delete':
            student_id = request.form.get('student_id')
            try:
                # 先删除选课记录
                cursor.execute("DELETE FROM course_selection WHERE student_id=%s", (student_id,))
                # 删除用户角色记录
                cursor.execute("DELETE FROM user_role WHERE user_id=%s", (student_id,))
                # 最后删除学生记录
                cursor.execute("DELETE FROM student WHERE student_id=%s", (student_id,))
                conn.commit()
            except Exception as e:
                conn.rollback()
                error = str(e)
                return render_template('admin_manage_students.html', error=error)
        
        elif action == 'reset_password':
            student_id = request.form.get('student_id')
            new_password = request.form.get('new_password', '123456')  # 默认密码为123456
            
            try:
                # 更新user_role表中的密码
                sql_update = """
                UPDATE user_role 
                SET password = MD5(%s) 
                WHERE user_id = %s
                """
                cursor.execute(sql_update, (new_password, student_id))
                
                # 检查是否更新了记录
                if cursor.rowcount == 0:
                    # 如果学生ID不在user_role表中，可能是之前添加时没有创建账号
                    # 尝试插入用户记录
                    sql_insert_user = """
                    INSERT INTO user_role (user_id, role, password)
                    VALUES (%s, 'student', MD5(%s))
                    """
                    cursor.execute(sql_insert_user, (student_id, new_password))
                
                conn.commit()
            except Exception as e:
                conn.rollback()
                error = str(e)
                return render_template('admin_manage_students.html', error=error)

    # 查询所有学生信息 - 添加搜索功能
    search_query = request.args.get('search', '')
    if search_query:
        sql_search = """
            SELECT s.*, d.dept_name 
            FROM student s 
            LEFT JOIN department d ON s.dept_id = d.dept_id
            WHERE s.student_id LIKE %s OR s.name LIKE %s
            ORDER BY s.student_id
        """
        cursor.execute(sql_search, (f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute("""
            SELECT s.*, d.dept_name 
            FROM student s 
            LEFT JOIN department d ON s.dept_id = d.dept_id
            ORDER BY s.student_id
        """)
    students = cursor.fetchall()

    # 查询所有院系信息用于添加学生时选择
    cursor.execute("SELECT dept_id, dept_name FROM department")
    departments = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('admin_manage_students.html', students=students, departments=departments, search_query=search_query)


@app.route('/admin/courses', methods=['GET', 'POST'])
def admin_manage_courses():
    """管理员管理课程功能"""
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            course_id = request.form.get('course_id')
            course_name = request.form.get('course_name')
            credit = request.form.get('credit')
            credit_hours = request.form.get('credit_hours')
            dept_id = request.form.get('dept_id')

            try:
                sql_insert = """
                INSERT INTO course (course_id, course_name, credit, credit_hours, dept_id)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(sql_insert, (course_id, course_name, credit, credit_hours, dept_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                error = str(e)
                return render_template('admin_manage_courses.html', error=error)

        elif action == 'delete':
            course_id = request.form.get('course_id')
            try:
                # 先删除相关的开课记录
                cursor.execute("DELETE FROM class WHERE course_id=%s", (course_id,))
                # 删除选课记录
                cursor.execute("DELETE FROM course_selection WHERE course_id=%s", (course_id,))
                # 最后删除课程记录
                cursor.execute("DELETE FROM course WHERE course_id=%s", (course_id,))
                conn.commit()
            except Exception as e:
                conn.rollback()
                error = str(e)
                return render_template('admin_manage_courses.html', error=error)

    # 查询所有课程信息 - 添加搜索功能
    search_query = request.args.get('search', '')
    if search_query:
        sql_search = """
            SELECT c.*, d.dept_name 
            FROM course c 
            LEFT JOIN department d ON c.dept_id = d.dept_id
            WHERE c.course_id LIKE %s OR c.course_name LIKE %s
            ORDER BY c.course_id
        """
        cursor.execute(sql_search, (f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute("""
            SELECT c.*, d.dept_name 
            FROM course c 
            LEFT JOIN department d ON c.dept_id = d.dept_id
            ORDER BY c.course_id
        """)
    courses = cursor.fetchall()

    # 查询所有院系信息用于添加课程时选择
    cursor.execute("SELECT dept_id, dept_name FROM department")
    departments = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('admin_manage_courses.html', courses=courses, departments=departments, search_query=search_query)


@app.route('/admin/departments', methods=['GET', 'POST'])
def admin_manage_departments():
    """管理员管理院系功能"""
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            dept_id = request.form.get('dept_id')
            dept_name = request.form.get('dept_name')
            address = request.form.get('address')
            phone_code = request.form.get('phone_code')

            try:
                sql_insert = """
                INSERT INTO department (dept_id, dept_name, address, phone_code)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql_insert, (dept_id, dept_name, address, phone_code))
                conn.commit()
            except Exception as e:
                conn.rollback()
                error = str(e)
                return render_template('admin_manage_departments.html', error=error)

        elif action == 'delete':
            dept_id = request.form.get('dept_id')
            try:
                # 检查是否有学生或教师属于该院系
                cursor.execute("SELECT COUNT(*) as count FROM student WHERE dept_id=%s", (dept_id,))
                student_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM teacher WHERE dept_id=%s", (dept_id,))
                teacher_count = cursor.fetchone()['count']
                
                if student_count > 0 or teacher_count > 0:
                    error = "无法删除院系：该院系下还有学生或教师，请先转移或删除相关记录"
                    return render_template('admin_manage_departments.html', error=error)
                
                # 删除院系记录
                cursor.execute("DELETE FROM department WHERE dept_id=%s", (dept_id,))
                conn.commit()
            except Exception as e:
                conn.rollback()
                error = str(e)
                return render_template('admin_manage_departments.html', error=error)

    # 查询所有院系信息
    cursor.execute("SELECT * FROM department ORDER BY dept_id")
    departments = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('admin_manage_departments.html', departments=departments)


@app.route('/admin/course_detail/<course_id>/<staff_id>/<semester>', methods=['GET', 'POST'])
def admin_course_detail(course_id, staff_id, semester):
    """管理员查看课程详细信息，包括教师和学生"""
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # 获取课程信息
    cursor.execute("""
        SELECT c.course_name, t.name as teacher_name, d.dept_name, c.credit, c.credit_hours
        FROM course c
        JOIN teacher t ON c.dept_id = t.dept_id
        JOIN department d ON c.dept_id = d.dept_id
        WHERE c.course_id = %s
    """, (course_id,))
    course_info = cursor.fetchone()

    # 获取当前课程的教师信息
    cursor.execute("""
        SELECT t.name as teacher_name, t.staff_id
        FROM teacher t
        WHERE t.staff_id = %s
    """, (staff_id,))
    teacher_info = cursor.fetchone()

    # 获取当前课程的学生列表
    cursor.execute("""
        SELECT s.student_id, s.name as student_name, cs.normal_score, cs.test_score, cs.total_score
        FROM course_selection cs
        JOIN student s ON cs.student_id = s.student_id
        WHERE cs.course_id = %s AND cs.staff_id = %s AND cs.semester = %s
        ORDER BY s.student_id
    """, (course_id, staff_id, semester))
    enrolled_students = cursor.fetchall()

    # 获取未选该课程的学生列表
    cursor.execute("""
        SELECT s.student_id, s.name as student_name
        FROM student s
        WHERE s.student_id NOT IN (
            SELECT cs.student_id
            FROM course_selection cs
            WHERE cs.course_id = %s AND cs.staff_id = %s AND cs.semester = %s
        )
        ORDER BY s.student_id
    """, (course_id, staff_id, semester))
    available_students = cursor.fetchall()

    # 获取所有教师列表（用于更换教师）
    cursor.execute("""
        SELECT t.staff_id, t.name as teacher_name
        FROM teacher t
        WHERE t.dept_id = (
            SELECT dept_id FROM course WHERE course_id = %s
        )
    """, (course_id,))
    all_teachers = cursor.fetchall()

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_student':
            student_id = request.form.get('student_id')
            try:
                sql_insert = """
                INSERT INTO course_selection (student_id, semester, course_id, staff_id)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql_insert, (student_id, semester, course_id, staff_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                error = str(e)
                return render_template('admin_course_detail.html', 
                                       course_info=course_info, 
                                       teacher_info=teacher_info,
                                       enrolled_students=enrolled_students,
                                       available_students=available_students,
                                       all_teachers=all_teachers,
                                       semester=semester,
                                       error=error)
        
        elif action == 'remove_student':
            student_id = request.form.get('student_id')
            try:
                cursor.execute("""
                    DELETE FROM course_selection 
                    WHERE student_id = %s AND semester = %s AND course_id = %s AND staff_id = %s
                """, (student_id, semester, course_id, staff_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                error = str(e)
                return render_template('admin_course_detail.html', 
                                       course_info=course_info, 
                                       teacher_info=teacher_info,
                                       enrolled_students=enrolled_students,
                                       available_students=available_students,
                                       all_teachers=all_teachers,
                                       semester=semester,
                                       error=error)
        
        elif action == 'change_teacher':
            new_staff_id = request.form.get('new_teacher_id')
            try:
                cursor.execute("""
                    UPDATE course_selection 
                    SET staff_id = %s 
                    WHERE course_id = %s AND staff_id = %s AND semester = %s
                """, (new_staff_id, course_id, staff_id, semester))
                conn.commit()
            except Exception as e:
                conn.rollback()
                error = str(e)
                return render_template('admin_course_detail.html', 
                                       course_info=course_info, 
                                       teacher_info=teacher_info,
                                       enrolled_students=enrolled_students,
                                       available_students=available_students,
                                       all_teachers=all_teachers,
                                       semester=semester,
                                       error=error)
        
        # 重新获取数据以更新页面
        cursor.execute("""
            SELECT s.student_id, s.name as student_name, cs.normal_score, cs.test_score, cs.total_score
            FROM course_selection cs
            JOIN student s ON cs.student_id = s.student_id
            WHERE cs.course_id = %s AND cs.staff_id = %s AND cs.semester = %s
            ORDER BY s.student_id
        """, (course_id, new_staff_id if 'new_staff_id' in locals() else staff_id, semester))
        enrolled_students = cursor.fetchall()

        cursor.execute("""
            SELECT s.student_id, s.name as student_name
            FROM student s
            WHERE s.student_id NOT IN (
                SELECT cs.student_id
                FROM course_selection cs
                WHERE cs.course_id = %s AND cs.staff_id = %s AND cs.semester = %s
            )
            ORDER BY s.student_id
        """, (course_id, new_staff_id if 'new_staff_id' in locals() else staff_id, semester))
        available_students = cursor.fetchall()

        if 'new_staff_id' in locals():
            cursor.execute("""
                SELECT t.name as teacher_name, t.staff_id
                FROM teacher t
                WHERE t.staff_id = %s
            """, (new_staff_id,))
            teacher_info = cursor.fetchone()
            staff_id = new_staff_id

    cursor.close()
    conn.close()
    
    return render_template('admin_course_detail.html', 
                           course_info=course_info, 
                           teacher_info=teacher_info,
                           enrolled_students=enrolled_students,
                           available_students=available_students,
                           all_teachers=all_teachers,
                           semester=semester)


@app.route('/admin/classes/<course_id>', methods=['GET', 'POST'])
def admin_manage_classes(course_id):
    """管理员管理课程的开课信息"""
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # 获取课程信息
    cursor.execute("SELECT course_name FROM course WHERE course_id = %s", (course_id,))
    course_info = cursor.fetchone()

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            semester = request.form.get('semester')
            staff_id = request.form.get('staff_id')
            class_time = request.form.get('class_time')

            try:
                sql_insert = """
                INSERT INTO class (semester, course_id, staff_id, class_time)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql_insert, (semester, course_id, staff_id, class_time))
                conn.commit()
            except Exception as e:
                conn.rollback()
                error = str(e)
                # 重新获取教师列表用于页面显示
                cursor.execute("""
                    SELECT t.staff_id, t.name as teacher_name
                    FROM teacher t
                    WHERE t.dept_id = (SELECT dept_id FROM course WHERE course_id = %s)
                """, (course_id,))
                teachers = cursor.fetchall()
                # 获取当前开课列表
                cursor.execute("""
                    SELECT c.semester, c.staff_id, t.name as teacher_name, c.class_time
                    FROM class c
                    JOIN teacher t ON c.staff_id = t.staff_id
                    WHERE c.course_id = %s
                """, (course_id,))
                classes = cursor.fetchall()
                cursor.close()
                conn.close()
                return render_template('admin_manage_classes.html', 
                                       course_info=course_info, 
                                       course_id=course_id,
                                       teachers=teachers, 
                                       classes=classes, 
                                       error=error)

        elif action == 'delete':
            semester = request.form.get('semester')
            staff_id = request.form.get('staff_id')
            try:
                # 删除相关的选课记录
                cursor.execute("""
                    DELETE FROM course_selection 
                    WHERE course_id = %s AND staff_id = %s AND semester = %s
                """, (course_id, staff_id, semester))
                # 删除开课记录
                cursor.execute("""
                    DELETE FROM class 
                    WHERE course_id = %s AND staff_id = %s AND semester = %s
                """, (course_id, staff_id, semester))
                conn.commit()
            except Exception as e:
                conn.rollback()
                error = str(e)
                # 重新获取教师列表用于页面显示
                cursor.execute("""
                    SELECT t.staff_id, t.name as teacher_name
                    FROM teacher t
                    WHERE t.dept_id = (SELECT dept_id FROM course WHERE course_id = %s)
                """, (course_id,))
                teachers = cursor.fetchall()
                # 获取当前开课列表
                cursor.execute("""
                    SELECT c.semester, c.staff_id, t.name as teacher_name, c.class_time
                    FROM class c
                    JOIN teacher t ON c.staff_id = t.staff_id
                    WHERE c.course_id = %s
                """, (course_id,))
                classes = cursor.fetchall()
                cursor.close()
                conn.close()
                return render_template('admin_manage_classes.html', 
                                       course_info=course_info, 
                                       course_id=course_id,
                                       teachers=teachers, 
                                       classes=classes, 
                                       error=error)

    # 获取相关院系的教师列表
    cursor.execute("""
        SELECT t.staff_id, t.name as teacher_name
        FROM teacher t
        WHERE t.dept_id = (SELECT dept_id FROM course WHERE course_id = %s)
    """, (course_id,))
    teachers = cursor.fetchall()

    # 获取当前开课列表
    cursor.execute("""
        SELECT c.semester, c.staff_id, t.name as teacher_name, c.class_time
        FROM class c
        JOIN teacher t ON c.staff_id = t.staff_id
        WHERE c.course_id = %s
    """, (course_id,))
    classes = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('admin_manage_classes.html', 
                           course_info=course_info, 
                           course_id=course_id,
                           teachers=teachers, 
                           classes=classes)


@app.route('/admin/teachers', methods=['GET', 'POST'])
def admin_manage_teachers():
    """管理员管理教师功能"""
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            staff_id = request.form.get('staff_id')
            name = request.form.get('name')
            sex = request.form.get('sex')
            date_of_birth = request.form.get('date_of_birth')
            professional_ranks = request.form.get('professional_ranks')
            salary = request.form.get('salary')
            dept_id = request.form.get('dept_id')
            user_id = request.form.get('user_id', staff_id)  # 如果未指定用户ID，则使用工号
            password = request.form.get('password', '123456')  # 如果未指定密码，则使用默认密码

            try:
                sql_insert = """
                INSERT INTO teacher (staff_id, name, sex, date_of_birth, professional_ranks, salary, dept_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql_insert, (staff_id, name, sex, date_of_birth, professional_ranks, salary, dept_id))
                # 同时在user_role表中添加教师账号
                sql_insert_user = """
                INSERT INTO user_role (user_id, role, password)
                VALUES (%s, 'teacher', MD5(%s))
                """
                cursor.execute(sql_insert_user, (user_id, password))
                conn.commit()
            except Exception as e:
                conn.rollback()
                error = str(e)
                # 重新获取院系信息用于页面显示
                cursor.execute("SELECT dept_id, dept_name FROM department")
                departments = cursor.fetchall()
                # 获取当前教师列表
                cursor.execute("""
                    SELECT t.*, d.dept_name 
                    FROM teacher t 
                    LEFT JOIN department d ON t.dept_id = d.dept_id
                    ORDER BY t.staff_id
                """)
                teachers = cursor.fetchall()
                cursor.close()
                conn.close()
                return render_template('admin_manage_teachers.html', 
                                       teachers=teachers, 
                                       departments=departments, 
                                       error=error)

        elif action == 'delete':
            staff_id = request.form.get('staff_id')
            try:
                # 先删除相关的开课记录
                cursor.execute("DELETE FROM class WHERE staff_id=%s", (staff_id,))
                # 删除相关的选课记录
                cursor.execute("DELETE FROM course_selection WHERE staff_id=%s", (staff_id,))
                # 删除用户角色记录
                cursor.execute("DELETE FROM user_role WHERE user_id=%s", (staff_id,))
                # 最后删除教师记录
                cursor.execute("DELETE FROM teacher WHERE staff_id=%s", (staff_id,))
                conn.commit()
            except Exception as e:
                conn.rollback()
                error = str(e)
                # 重新获取院系信息用于页面显示
                cursor.execute("SELECT dept_id, dept_name FROM department")
                departments = cursor.fetchall()
                # 获取当前教师列表
                cursor.execute("""
                    SELECT t.*, d.dept_name 
                    FROM teacher t 
                    LEFT JOIN department d ON t.dept_id = d.dept_id
                    ORDER BY t.staff_id
                """)
                teachers = cursor.fetchall()
                cursor.close()
                conn.close()
                return render_template('admin_manage_teachers.html', 
                                       teachers=teachers, 
                                       departments=departments, 
                                       error=error)
        
        elif action == 'reset_password':
            staff_id = request.form.get('staff_id')
            new_password = request.form.get('new_password', '123456')  # 默认密码为123456
            
            try:
                # 更新user_role表中的密码
                sql_update = """
                UPDATE user_role 
                SET password = MD5(%s) 
                WHERE user_id = %s
                """
                cursor.execute(sql_update, (new_password, staff_id))
                
                # 检查是否更新了记录
                if cursor.rowcount == 0:
                    # 如果教师ID不在user_role表中，可能是之前添加时没有创建账号
                    # 尝试插入用户记录
                    sql_insert_user = """
                    INSERT INTO user_role (user_id, role, password)
                    VALUES (%s, 'teacher', MD5(%s))
                    """
                    cursor.execute(sql_insert_user, (staff_id, new_password))
                
                conn.commit()
            except Exception as e:
                conn.rollback()
                error = str(e)
                # 重新获取院系信息用于页面显示
                cursor.execute("SELECT dept_id, dept_name FROM department")
                departments = cursor.fetchall()
                # 获取当前教师列表
                cursor.execute("""
                    SELECT t.*, d.dept_name 
                    FROM teacher t 
                    LEFT JOIN department d ON t.dept_id = d.dept_id
                    ORDER BY t.staff_id
                """)
                teachers = cursor.fetchall()
                cursor.close()
                conn.close()
                return render_template('admin_manage_teachers.html', 
                                       teachers=teachers, 
                                       departments=departments, 
                                       error=error)

    # 查询所有教师信息 - 添加搜索功能
    search_query = request.args.get('search', '')
    if search_query:
        sql_search = """
            SELECT t.*, d.dept_name 
            FROM teacher t 
            LEFT JOIN department d ON t.dept_id = d.dept_id
            WHERE t.staff_id LIKE %s OR t.name LIKE %s
            ORDER BY t.staff_id
        """
        cursor.execute(sql_search, (f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute("""
            SELECT t.*, d.dept_name 
            FROM teacher t 
            LEFT JOIN department d ON t.dept_id = d.dept_id
            ORDER BY t.staff_id
        """)
    teachers = cursor.fetchall()

    # 查询所有院系信息用于添加教师时选择
    cursor.execute("SELECT dept_id, dept_name FROM department")
    departments = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('admin_manage_teachers.html', teachers=teachers, departments=departments, search_query=search_query)


@app.route('/admin/teacher-course-stats', methods=['GET', 'POST'])
def admin_teacher_course_stats():
    """管理员查看教师课程及选课学生数量统计"""
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    teachers = []
    selected_teacher = None
    course_stats = []

    try:
        # 获取所有教师列表用于下拉选择
        cursor.execute("""
            SELECT t.staff_id, t.name, d.dept_name 
            FROM teacher t 
            LEFT JOIN department d ON t.dept_id = d.dept_id
            ORDER BY t.staff_id
        """)
        teachers = cursor.fetchall()

        if request.method == 'POST':
            selected_teacher = request.form.get('teacher_id')
            if selected_teacher:
                # 调用存储过程获取指定教师的课程及选课学生数量
                cursor.callproc('sp_get_teacher_course_student_count', (selected_teacher,))
                # 获取存储过程的结果
                course_stats = cursor.fetchall()
        elif request.args.get('teacher_id'):
            # 通过GET请求直接查看某个教师的课程统计
            selected_teacher = request.args.get('teacher_id')
            cursor.callproc('sp_get_teacher_course_student_count', (selected_teacher,))
            course_stats = cursor.fetchall()

    except Exception as e:
        error = f"查询出错: {str(e)}"
        return render_template('admin_teacher_course_stats.html', 
                               teachers=teachers, 
                               selected_teacher=selected_teacher, 
                               course_stats=course_stats, 
                               error=error)
    finally:
        cursor.close()
        conn.close()

    return render_template('admin_teacher_course_stats.html', 
                           teachers=teachers, 
                           selected_teacher=selected_teacher, 
                           course_stats=course_stats)


@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    """管理员系统设置功能"""
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # 获取当前的设置
    cursor.execute("SELECT value FROM system_settings WHERE setting_key = 'allow_course_drop' LIMIT 1")
    drop_setting = cursor.fetchone()
    allow_drop = drop_setting['value'] == '1' if drop_setting else False

    cursor.execute("SELECT value FROM system_settings WHERE setting_key = 'allow_teacher_modify_scores' LIMIT 1")
    modify_setting = cursor.fetchone()
    allow_teacher_modify_scores = modify_setting['value'] == '1' if modify_setting else False

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'toggle_drop':
            new_status = request.form.get('new_status')
            try:
                # 检查设置记录是否存在
                cursor.execute("SELECT value FROM system_settings WHERE setting_key = 'allow_course_drop' LIMIT 1")
                exists = cursor.fetchone()
                
                if exists:
                    # 更新现有记录
                    cursor.execute("""
                        UPDATE system_settings 
                        SET value = %s 
                        WHERE setting_key = 'allow_course_drop'
                    """, (new_status,))
                else:
                    # 插入新记录
                    cursor.execute("""
                        INSERT INTO system_settings (setting_key, value) 
                        VALUES ('allow_course_drop', %s)
                    """, (new_status,))
                
                conn.commit()
                allow_drop = new_status == '1'
            except Exception as e:
                conn.rollback()
                error = str(e)
                cursor.close()
                conn.close()
                return render_template('admin_settings.html', 
                                       allow_drop=allow_drop, 
                                       allow_teacher_modify_scores=allow_teacher_modify_scores, 
                                       error=error)
        
        elif action == 'toggle_teacher_modify':
            new_status = request.form.get('new_status')
            try:
                # 检查设置记录是否存在
                cursor.execute("SELECT value FROM system_settings WHERE setting_key = 'allow_teacher_modify_scores' LIMIT 1")
                exists = cursor.fetchone()
                
                if exists:
                    # 更新现有记录
                    cursor.execute("""
                        UPDATE system_settings 
                        SET value = %s 
                        WHERE setting_key = 'allow_teacher_modify_scores'
                    """, (new_status,))
                else:
                    # 插入新记录
                    cursor.execute("""
                        INSERT INTO system_settings (setting_key, value) 
                        VALUES ('allow_teacher_modify_scores', %s)
                    """, (new_status,))
                
                conn.commit()
                allow_teacher_modify_scores = new_status == '1'
            except Exception as e:
                conn.rollback()
                error = str(e)
                cursor.close()
                conn.close()
                return render_template('admin_settings.html', 
                                       allow_drop=allow_drop, 
                                       allow_teacher_modify_scores=allow_teacher_modify_scores, 
                                       error=error)

    cursor.close()
    conn.close()
    return render_template('admin_settings.html', 
                           allow_drop=allow_drop, 
                           allow_teacher_modify_scores=allow_teacher_modify_scores)


if __name__ == '__main__':
    app.run(debug=True)  # 调试模式运行，生产环境关闭debug