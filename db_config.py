# 数据库连接配置
import pymysql

def get_db_connection():
    """获取数据库连接（极简封装）"""
    conn = pymysql.connect(
        host='localhost',  # 本地数据库
        user='root',       # 你的MySQL用户名
        password='password', # 你的MySQL密码
        database='school1', # 数据库名
        charset='utf8mb4'
    )
    return conn