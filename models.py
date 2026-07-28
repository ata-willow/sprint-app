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
        unit TEXT,
        log_type TEXT NOT NULL DEFAULT 'study',
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

    c.execute('''CREATE TABLE IF NOT EXISTS mock_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        score REAL NOT NULL,
        date TEXT NOT NULL,
        exam_name TEXT,
        created_at TEXT NOT NULL
    )''')

    # 迁移：为旧表添加新字段
    for col, col_type in [('unit', 'TEXT'), ('log_type', "TEXT NOT NULL DEFAULT 'study'")]:
        try:
            c.execute(f'ALTER TABLE logs ADD COLUMN {col} {col_type}')
        except Exception:
            pass

    try:
        c.execute('ALTER TABLE mock_scores ADD COLUMN exam_name TEXT')
    except Exception:
        pass

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

def add_log(date, subject, duration_hours, content, mood, insight=None, unit=None, log_type='study'):
    """添加一条学习记录"""
    conn = get_db()
    c = conn.cursor()
    created_at = datetime.now().isoformat()
    c.execute(
        'INSERT INTO logs (date, subject, duration_hours, content, mood, insight, unit, log_type, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (date, subject, duration_hours, content, mood, insight, unit, log_type, created_at)
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

    # 总学习时长（仅study类型）
    c.execute("SELECT COALESCE(SUM(duration_hours), 0) FROM logs WHERE log_type = 'study'")
    total_hours = c.fetchone()[0]

    # 各科学习时长
    c.execute("SELECT subject, SUM(duration_hours) as hours FROM logs WHERE log_type = 'study' GROUP BY subject ORDER BY hours DESC")
    by_subject = [{'subject': r['subject'], 'hours': r['hours']} for r in c.fetchall()]

    # 连续打卡天数
    c.execute("SELECT DISTINCT date FROM logs WHERE log_type = 'study' ORDER BY date DESC")
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
    c.execute("SELECT subject, COUNT(*) as count FROM logs WHERE log_type = 'study' GROUP BY subject ORDER BY count DESC")
    by_count = [{'subject': r['subject'], 'count': r['count']} for r in c.fetchall()]

    # 总记录数
    c.execute("SELECT COUNT(*) FROM logs WHERE log_type = 'study'")
    total_logs = c.fetchone()[0]

    # 各科最新模考分数
    c.execute('''SELECT ms.subject, ms.score, ms.date, ms.exam_name FROM mock_scores ms
                 INNER JOIN (
                   SELECT subject, MAX(date) as max_date FROM mock_scores GROUP BY subject
                 ) latest ON ms.subject = latest.subject AND ms.date = latest.max_date
                 ORDER BY ms.subject''')
    latest_mock_scores = [{'subject': r['subject'], 'score': r['score'], 'date': r['date'], 'exam_name': (dict(r)['exam_name'] if 'exam_name' in dict(r) else '')} for r in c.fetchall()]

    conn.close()
    return {
        'total_hours': round(total_hours, 1),
        'by_subject': by_subject,
        'streak': streak,
        'insights': insights,
        'by_count': by_count,
        'total_logs': total_logs,
        'latest_mock_scores': latest_mock_scores,
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


# ========== mock_scores 操作 ==========

def add_mock_score(subject, score, date, exam_name=None):
    """添加一条模考分数记录"""
    conn = get_db()
    c = conn.cursor()
    created_at = datetime.now().isoformat()
    c.execute(
        'INSERT INTO mock_scores (subject, score, date, exam_name, created_at) VALUES (?, ?, ?, ?, ?)',
        (subject, score, date, exam_name, created_at)
    )
    score_id = c.lastrowid
    conn.commit()
    conn.close()
    return score_id


def get_mock_scores(subject=None, limit=30):
    """获取模考分数列表，可按科目筛选"""
    conn = get_db()
    c = conn.cursor()
    if subject:
        c.execute('SELECT * FROM mock_scores WHERE subject = ? ORDER BY date DESC, created_at DESC LIMIT ?',
                  (subject, limit))
    else:
        c.execute('SELECT * FROM mock_scores ORDER BY date DESC, created_at DESC LIMIT ?', (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


# ========== 混合时间线 ==========

def get_timeline(limit=30):
    """获取混合时间线：学习日志 + 模考记录，按日期倒序排列"""
    conn = get_db()
    c = conn.cursor()

    # 获取学习记录
    c.execute("SELECT id, date, subject, duration_hours, content, mood, insight, unit, log_type, created_at FROM logs ORDER BY date DESC, created_at DESC LIMIT ?", (limit,))
    study_rows = [dict(r) for r in c.fetchall()]

    # 获取模考记录
    c.execute('SELECT id, date, subject, score, exam_name, created_at FROM mock_scores ORDER BY date DESC, created_at DESC LIMIT ?', (limit,))
    mock_rows = [dict(r) for r in c.fetchall()]

    conn.close()

    # 标记类型
    for r in study_rows:
        r['timeline_type'] = 'study'
    for r in mock_rows:
        r['timeline_type'] = 'mock'

    # 合并并按日期倒序排列
    all_items = study_rows + mock_rows
    all_items.sort(key=lambda x: (x['date'], x.get('created_at', '')), reverse=True)

    return all_items[:limit]


# ========== 学科预测分 ==========

def get_subject_predictions():
    """根据模考分数趋势，简单线性回归预测最终分数"""
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT subject, score, date FROM mock_scores ORDER BY date ASC')
    rows = c.fetchall()
    conn.close()

    if not rows:
        return {}

    subject_scores = {}
    for r in rows:
        sub = r['subject']
        if sub not in subject_scores:
            subject_scores[sub] = []
        subject_scores[sub].append((r['date'], r['score']))

    predictions = {}
    for sub, scores in subject_scores.items():
        n = len(scores)
        if n < 2:
            predictions[sub] = round(scores[0][1], 1)
            continue

        xs = list(range(n))
        ys = [s[1] for s in scores]
        x_mean = sum(xs) / n
        y_mean = sum(ys) / n
        numerator = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
        denominator = sum((xs[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            predictions[sub] = round(y_mean, 1)
            continue

        b = numerator / denominator
        a = y_mean - b * x_mean
        predicted = a + b * n

        if sub == '托福':
            predicted = max(0, min(120, predicted))
        else:
            predicted = max(0, min(5, predicted))

        predictions[sub] = round(predicted, 1)

    return predictions


# ========== 年度热力图数据 ==========

def get_yearly_heatmap(year=None):
    """获取指定年份每天的学习记录标记数据"""
    if year is None:
        year = datetime.now().year

    conn = get_db()
    c = conn.cursor()

    c.execute(
        "SELECT date, SUM(duration_hours) as hours FROM logs WHERE date LIKE ? AND log_type = 'study' GROUP BY date ORDER BY date",
        (f'{year}-%',)
    )
    rows = c.fetchall()
    conn.close()

    heatmap = {}
    for r in rows:
        heatmap[r['date']] = round(r['hours'], 1)

    return {'year': year, 'heatmap': heatmap}
