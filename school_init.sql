/* 专门用于直接复制粘贴的版本 */

-- 1.  GBK 编码
SET NAMES gbk;
SET FOREIGN_KEY_CHECKS = 0;

-- 2. 重建数据库
DROP DATABASE IF EXISTS `school1`;
CREATE DATABASE `school1` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `school1`;

-- 3. 创建表结构
CREATE TABLE `department` (
  `dept_id` varchar(10) NOT NULL,
  `dept_name` varchar(50) NOT NULL,
  `address` varchar(100) DEFAULT NULL,
  `phone_code` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`dept_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `student` (
  `student_id` varchar(10) NOT NULL,
  `name` varchar(20) NOT NULL,
  `sex` enum('男','女') NOT NULL,
  `date_of_birth` date NOT NULL,
  `native_place` varchar(50) DEFAULT NULL,
  `mobile_phone` varchar(20) DEFAULT NULL,
  `dept_id` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`student_id`),
  KEY `dept_id` (`dept_id`),
  CONSTRAINT `student_ibfk_1` FOREIGN KEY (`dept_id`) REFERENCES `department` (`dept_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `teacher` (
  `staff_id` varchar(10) NOT NULL,
  `name` varchar(20) NOT NULL,
  `sex` enum('男','女') NOT NULL,
  `date_of_birth` date NOT NULL,
  `professional_ranks` varchar(20) NOT NULL,
  `salary` decimal(10,2) NOT NULL,
  `dept_id` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`staff_id`),
  KEY `dept_id` (`dept_id`),
  CONSTRAINT `teacher_ibfk_1` FOREIGN KEY (`dept_id`) REFERENCES `department` (`dept_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `course` (
  `course_id` varchar(20) NOT NULL,
  `course_name` varchar(50) NOT NULL,
  `credit` int DEFAULT '4',
  `credit_hours` int DEFAULT '40',
  `dept_id` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`course_id`),
  KEY `dept_id` (`dept_id`),
  CONSTRAINT `course_ibfk_1` FOREIGN KEY (`dept_id`) REFERENCES `department` (`dept_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `class` (
  `semester` varchar(20) NOT NULL,
  `course_id` varchar(20) NOT NULL,
  `staff_id` varchar(10) NOT NULL,
  `class_time` varchar(20) NOT NULL,
  `normal_ratio` int DEFAULT '30',
  `test_ratio` int DEFAULT '70',
  PRIMARY KEY (`semester`,`course_id`,`staff_id`),
  KEY `course_id` (`course_id`),
  KEY `staff_id` (`staff_id`),
  CONSTRAINT `class_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `course` (`course_id`),
  CONSTRAINT `class_ibfk_2` FOREIGN KEY (`staff_id`) REFERENCES `teacher` (`staff_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `course_selection` (
  `student_id` varchar(10) NOT NULL,
  `semester` varchar(20) NOT NULL,
  `course_id` varchar(20) NOT NULL,
  `staff_id` varchar(10) NOT NULL,
  `normal_score` int DEFAULT NULL,
  `test_score` int DEFAULT NULL,
  `total_score` int DEFAULT NULL,
  PRIMARY KEY (`student_id`,`semester`,`course_id`,`staff_id`),
  KEY `semester` (`semester`,`course_id`,`staff_id`),
  CONSTRAINT `course_selection_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`),
  CONSTRAINT `course_selection_ibfk_2` FOREIGN KEY (`semester`, `course_id`, `staff_id`) REFERENCES `class` (`semester`, `course_id`, `staff_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `user_role` (
  `user_id` varchar(10) NOT NULL,
  `role` enum('admin','teacher','student') NOT NULL,
  `password` varchar(32) DEFAULT NULL,
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `system_settings` (
  `setting_key` varchar(50) NOT NULL,
  `value` varchar(100) NOT NULL,
  PRIMARY KEY (`setting_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 插入数据
INSERT INTO `system_settings` VALUES ('allow_course_drop', '0');
INSERT INTO `system_settings` VALUES ('allow_teacher_modify_scores', '0');

INSERT INTO `department` VALUES ('01', '计算机学院', '上大东校区三号楼', '65347567');
INSERT INTO `department` VALUES ('02', '通讯学院', '上大东校区二号楼', '65341234');
INSERT INTO `department` VALUES ('03', '材料学院', '上大东校区四号楼', '65347890');

INSERT INTO `teacher` VALUES ('0101', '陈迪茂', '男', '1973-03-06', '副教授', 3567.00, '01');
INSERT INTO `teacher` VALUES ('0102', '马小红', '女', '1972-12-08', '讲师', 2845.00, '01');
INSERT INTO `teacher` VALUES ('0103', '吴宝钢', '男', '1980-11-06', '讲师', 2554.00, '01');
INSERT INTO `teacher` VALUES ('0201', '张心颖', '女', '1970-01-05', '教授', 4200.00, '02');

INSERT INTO `student` VALUES ('1101', '李明', '男', '1993-03-06', '上海', '13613005486', '02');
INSERT INTO `student` VALUES ('1102', '刘晓明', '男', '1992-12-08', '安徽', '18913457890', '01');
INSERT INTO `student` VALUES ('1103', '张颖', '女', '1993-01-05', '江苏', '18826490423', '01');
INSERT INTO `student` VALUES ('1104', '刘晶晶', '女', '1994-11-06', '上海', '13331934111', '01');
INSERT INTO `student` VALUES ('1105', '刘成刚', '男', '1991-06-07', '上海', '18015872567', '01');
INSERT INTO `student` VALUES ('1106', '李二丽', '女', '1993-05-04', '江苏', '18107620945', '01');
INSERT INTO `student` VALUES ('1107', '张晓峰', '男', '1992-08-16', '浙江', '13912341078', '01');

INSERT INTO `course` VALUES ('08301001', '分子物理学', 4, 40, '03');
INSERT INTO `course` VALUES ('08302001', '通信学', 3, 30, '02');
INSERT INTO `course` VALUES ('08305001', '离散数学', 4, 40, '01');
INSERT INTO `course` VALUES ('08305002', '数据库原理', 4, 50, '01');
INSERT INTO `course` VALUES ('08305003', '数据结构', 4, 50, '01');
INSERT INTO `course` VALUES ('08305004', '系统结构', 6, 60, '01');

INSERT INTO `class` VALUES ('2013-2014秋季', '08305001', '0102', '星期一5-8', 30, 70);
INSERT INTO `class` VALUES ('2012-2013秋季', '08305001', '0103', '星期三5-8', 30, 70);
INSERT INTO `class` VALUES ('2012-2013冬季', '08305002', '0101', '星期三1-4', 30, 70);
INSERT INTO `class` VALUES ('2012-2013冬季', '08305002', '0102', '星期三1-4', 30, 70);
INSERT INTO `class` VALUES ('2012-2013冬季', '08305002', '0103', '星期三1-4', 30, 70);
INSERT INTO `class` VALUES ('2012-2013冬季', '08305003', '0102', '星期五5-8', 30, 70);
INSERT INTO `class` VALUES ('2013-2014秋季', '08305004', '0101', '星期二1-4', 30, 70);
INSERT INTO `class` VALUES ('2013-2014冬季', '08302001', '0201', '星期一5-8', 30, 70);

INSERT INTO `course_selection` VALUES ('1102', '2013-2014秋季', '08305004', '0101', NULL, NULL, NULL);
INSERT INTO `course_selection` VALUES ('1103', '2013-2014秋季', '08305004', '0101', NULL, NULL, NULL);
INSERT INTO `course_selection` VALUES ('1107', '2013-2014秋季', '08305004', '0101', NULL, NULL, NULL);
INSERT INTO `course_selection` VALUES ('1103', '2013-2014秋季', '08305001', '0102', NULL, NULL, NULL);
INSERT INTO `course_selection` VALUES ('1101', '2012-2013秋季', '08305001', '0103', 60, 60, 60);
INSERT INTO `course_selection` VALUES ('1102', '2012-2013秋季', '08305001', '0103', 87, 87, 87);
INSERT INTO `course_selection` VALUES ('1103', '2012-2013秋季', '08305001', '0103', 56, 56, 56);
INSERT INTO `course_selection` VALUES ('1104', '2012-2013秋季', '08305001', '0103', 74, 74, 74);
INSERT INTO `course_selection` VALUES ('1106', '2012-2013秋季', '08305001', '0103', 85, 85, 85);
INSERT INTO `course_selection` VALUES ('1107', '2012-2013秋季', '08305001', '0103', 90, 90, 90);
INSERT INTO `course_selection` VALUES ('1102', '2012-2013冬季', '08305002', '0101', 82, 82, 82);
INSERT INTO `course_selection` VALUES ('1103', '2012-2013冬季', '08305002', '0102', 75, 75, 75);
INSERT INTO `course_selection` VALUES ('1103', '2012-2013冬季', '08305003', '0102', 84, 84, 84);
INSERT INTO `course_selection` VALUES ('1107', '2012-2013冬季', '08305003', '0102', 79, 79, 79);
INSERT INTO `course_selection` VALUES ('1106', '2012-2013冬季', '08305002', '0103', 66, 66, 66);
INSERT INTO `course_selection` VALUES ('1104', '2013-2014冬季', '08302001', '0201', NULL, NULL, NULL);

INSERT INTO `user_role` VALUES ('admin', 'admin', 'e10adc3949ba59abbe56e057f20f883e');
INSERT INTO `user_role` VALUES ('0101', 'teacher', 'e10adc3949ba59abbe56e057f20f883e');
INSERT INTO `user_role` VALUES ('0102', 'teacher', 'e10adc3949ba59abbe56e057f20f883e');
INSERT INTO `user_role` VALUES ('0103', 'teacher', 'e10adc3949ba59abbe56e057f20f883e');
INSERT INTO `user_role` VALUES ('0201', 'teacher', 'e10adc3949ba59abbe56e057f20f883e');
INSERT INTO `user_role` VALUES ('1101', 'student', 'e10adc3949ba59abbe56e057f20f883e');
INSERT INTO `user_role` VALUES ('1102', 'student', 'e10adc3949ba59abbe56e057f20f883e');
INSERT INTO `user_role` VALUES ('1103', 'student', 'e10adc3949ba59abbe56e057f20f883e');
INSERT INTO `user_role` VALUES ('1104', 'student', 'e10adc3949ba59abbe56e057f20f883e');
INSERT INTO `user_role` VALUES ('1105', 'student', 'e10adc3949ba59abbe56e057f20f883e');
INSERT INTO `user_role` VALUES ('1106', 'student', 'e10adc3949ba59abbe56e057f20f883e');
INSERT INTO `user_role` VALUES ('1107', 'student', 'e10adc3949ba59abbe56e057f20f883e');

-- 5. 存储过程与触发器
DELIMITER $$

CREATE PROCEDURE `sp_get_student_credit`(
    IN p_student_id VARCHAR(10),
    OUT p_total_credit INT
)
BEGIN
    SELECT IFNULL(SUM(c.credit), 0) INTO p_total_credit
    FROM course_selection cs
    JOIN course c ON cs.course_id = c.course_id
    WHERE cs.student_id = p_student_id AND cs.total_score >= 60;
END$$

CREATE PROCEDURE `sp_get_teacher_course_student_count`(IN p_staff_id VARCHAR(10))
BEGIN
    SELECT
        c.course_name AS `课程名称`,
        cl.semester AS `学期`,
        cl.class_time AS `上课时间`,
        COUNT(cs.student_id) AS `选课学生数量`
    FROM class cl
    JOIN course c ON cl.course_id = c.course_id
    LEFT JOIN course_selection cs ON cl.course_id = cs.course_id AND cl.semester = cs.semester AND cl.staff_id = cs.staff_id
    WHERE cl.staff_id = p_staff_id
    GROUP BY cl.semester, cl.course_id, cl.staff_id, c.course_name, cl.class_time
    ORDER BY cl.semester, c.course_name;
END$$

CREATE TRIGGER `trg_calc_total_score`
BEFORE INSERT ON `course_selection`
FOR EACH ROW
BEGIN
    DECLARE v_normal_ratio DECIMAL(3,2) DEFAULT 0.3;
    DECLARE v_test_ratio DECIMAL(3,2) DEFAULT 0.7;

    SELECT normal_ratio/100, test_ratio/100 INTO v_normal_ratio, v_test_ratio
    FROM class
    WHERE course_id = NEW.course_id AND staff_id = NEW.staff_id AND semester = NEW.semester
    LIMIT 1;

    IF NEW.normal_score IS NOT NULL AND NEW.test_score IS NOT NULL THEN
        SET NEW.total_score = ROUND(NEW.normal_score * v_normal_ratio + NEW.test_score * v_test_ratio);
    END IF;
END$$

CREATE TRIGGER `trg_update_total_score`
BEFORE UPDATE ON `course_selection`
FOR EACH ROW
BEGIN
    DECLARE v_normal_ratio DECIMAL(3,2) DEFAULT 0.3;
    DECLARE v_test_ratio DECIMAL(3,2) DEFAULT 0.7;

    SELECT normal_ratio/100, test_ratio/100 INTO v_normal_ratio, v_test_ratio
    FROM class
    WHERE course_id = NEW.course_id AND staff_id = NEW.staff_id AND semester = NEW.semester
    LIMIT 1;

    IF NEW.normal_score IS NOT NULL AND NEW.test_score IS NOT NULL THEN
        SET NEW.total_score = ROUND(NEW.normal_score * v_normal_ratio + NEW.test_score * v_test_ratio);
    ELSE
        SET NEW.total_score = NULL;
    END IF;
END$$

DELIMITER ;
SET FOREIGN_KEY_CHECKS = 1;