"""Sprint 数据模型 - SQLite 初始化与操作"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'sprint.db')

MILESTONES_INIT = [
    (1, "启航港口", "旅程的起点，扬帆起航", True, "2025-09-01"),
    (2, "托福90+港湾", "托福突破90分大关", False, None),
    (3, "物理1·五分礁", "AP Physics 1 拿下5分", False, None),
    (4, "统计学·五分滩", "AP Statistics 拿下5分", False, None),
    (5, "微积分BC·五分湾", "AP Calculus BC 拿下5分", False, None),
    (6, "物理C·五分岬", "AP Physics C 保4争5", False, None),
    (7, "⭐核心灯塔", "托福100+3门AP5+物理C≥4", False, None),
    (8, "密歇根安娜堡", "北线·美本", False, None),
    (9, "UCL", "南线·英本", False, None),
    (10, "提交申请港", "终点·所有申请提交完毕", False, None),
]


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表和初始数据"""
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        subject TEXT NOT NULL,
        duration_hours REAL NOT NULL,
        content TEXT,
        mood TEXT,
        insight TEXT,
        created_at TEXT NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS milestones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        order_num INTEGER NOT NULL,
        description TEXT,
        reached INTEGER NOT NULL DEFAULT 0,
        reached_date TEXT,
        UNIQUE(order_num)
    )''')

    # 初始化航点数据（仅当表为空时）
    c.execute('SELECT COUNT(*) FROM milestones')
    if c.fetchone()[0] == 0:
        for order_num, name, desc, reached, reached_date in MILESTONES_INIT:
            c.execute(
                'INSERT INTO milestones (name, order_num, description, reached, reached_date) VALUES (?, ?, ?, ?, ?)',
                (name, order_num, desc, 1 if reached else 0, reached_date)
            )

    conn.commit()
    conn.close()


# ========== logs 操作 ==========

def add_log(date, subject, duration_hours, content, mood, insight=None):
    """添加一条学习记录"""
    conn = get_db()
    c = conn.cursor()
    created_at = datetime.now().isoformat()
    c.execute(
        'INSERT INTO logs (date, subject, duration_hours, content, mood, insight, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (date, subject, duration_hours, content, mood, insight, created_at)
    )
    log_id = c.lastrowid
    conn.commit()
    conn.close()
    return log_id


def get_logs(limit=50, offset=0):
    """获取学习记录列表"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM logs ORDER BY date DESC, created_at DESC LIMIT ? OFFSET ?', (limit, offset))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_stats():
    """获取统计数据"""
    conn = get_db()
    c = conn.cursor()

    # 总学习时长
    c.execute('SELECT COALESCE(SUM(duration_hours), 0) FROM logs')
    total_hours = c.fetchone()[0]

    # 各科学习时长
    c.execute('SELECT subject, SUM(duration_hours) as hours FROM logs GROUP BY subject ORDER BY hours DESC')
    by_subject = [{'subject': r['subject'], 'hours': r['hours']} for r in c.fetchall()]

    # 连续打卡天数
    c.execute('SELECT DISTINCT date FROM logs ORDER BY date DESC')
    dates = [r['date'] for r in c.fetchall()]
    streak = 0
    if dates:
        from datetime import date as date_type
        today = date_type.today()
        for i, d in enumerate(dates):
            expected = today - __import__('datetime').timedelta(days=i)
            if d == expected.isoformat():
                streak += 1
            else:
                break

    # 顿悟时刻
    c.execute("SELECT id, date, subject, insight FROM logs WHERE insight IS NOT NULL AND insight != '' ORDER BY date DESC")
    insights = [dict(r) for r in c.fetchall()]

    # 各科记录数
    c.execute('SELECT subject, COUNT(*) as count FROM logs GROUP BY subject ORDER BY count DESC')
    by_count = [{'subject': r['subject'], 'count': r['count']} for r in c.fetchall()]

    # 总记录数
    c.execute('SELECT COUNT(*) FROM logs')
    total_logs = c.fetchone()[0]

    conn.close()
    return {
        'total_hours': round(total_hours, 1),
        'by_subject': by_subject,
        'streak': streak,
        'insights': insights,
        'by_count': by_count,
        'total_logs': total_logs,
    }


# ========== milestones 操作 ==========

def get_milestones():
    """获取所有航点"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM milestones ORDER BY order_num')
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def update_milestone(order_num, reached, reached_date=None):
    """更新航点状态"""
    conn = get_db()
    c = conn.cursor()
    if reached_date is None and reached:
        reached_date = datetime.now().strftime('%Y-%m-%d')
    c.execute(
        'UPDATE milestones SET reached = ?, reached_date = ? WHERE order_num = ?',
        (1 if reached else 0, reached_date, order_num)
    )
    conn.commit()
    updated = c.rowcount > 0
    conn.close()
    return updated
