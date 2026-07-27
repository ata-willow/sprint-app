"""Sprint - 航海主题学习打卡 PWA"""
import os
import json
import requests as req_lib
from flask import Flask, render_template, request, jsonify
from models import init_db, add_log, get_logs, get_stats, get_milestones, update_milestone

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL = 'https://api.deepseek.com/v1/chat/completions'

# 启动时初始化数据库
init_db()


# ========== 页面路由 ==========

def _mark_current_milestone(milestones):
    """给 milestones 列表标记 is_current 字段"""
    found_current = False
    for i, m in enumerate(milestones):
        if not m['reached'] and not found_current:
            if i == 0 or milestones[i - 1]['reached']:
                m['is_current'] = True
                found_current = True
            else:
                m['is_current'] = False
        else:
            m['is_current'] = False
    return milestones


@app.route('/')
def index():
    """航海页（首页）"""
    milestones = _mark_current_milestone(get_milestones())
    stats = get_stats()
    return render_template('index.html', milestones=milestones, stats=stats)


@app.route('/log')
def log_page():
    """日志页"""
    logs = get_logs(limit=30)
    stats = get_stats()
    return render_template('log.html', logs=logs, insights=stats.get('insights', []))


@app.route('/route')
def route_page():
    """航线页"""
    milestones = _mark_current_milestone(get_milestones())
    stats = get_stats()
    return render_template('route.html', milestones=milestones, stats=stats)


@app.route('/star')
def star_page():
    """星象页"""
    stats = get_stats()
    return render_template('index.html', milestones=[], stats={})


# ========== API 路由 ==========

@app.route('/api/log', methods=['POST'])
def api_add_log():
    """添加学习记录"""
    data = request.get_json(force=True)
    try:
        log_id = add_log(
            date=data['date'],
            subject=data['subject'],
            duration_hours=float(data['duration_hours']),
            content=data.get('content', ''),
            mood=data.get('mood', ''),
            insight=data.get('insight', None),
        )
        return jsonify({'ok': True, 'id': log_id})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@app.route('/api/logs')
def api_get_logs():
    """获取记录列表"""
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    logs = get_logs(limit=limit, offset=offset)
    return jsonify(logs)


@app.route('/api/stats')
def api_get_stats():
    """获取统计数据"""
    stats = get_stats()
    return jsonify(stats)


@app.route('/api/insights')
def api_insights():
    """AI 分析（DeepSeek）"""
    stats = get_stats()
    logs = get_logs(limit=20)

    # 构造分析 prompt
    summary_lines = []
    for s in stats.get('by_subject', []):
        summary_lines.append(f"- {s['subject']}: {s['hours']}小时")

    recent_lines = []
    for l in logs[:10]:
        insight_part = f"，顿悟：{l['insight']}" if l.get('insight') else ''
        recent_lines.append(f"  {l['date']} {l['subject']} {l['duration_hours']}h 心情{l.get('mood', '?')}{insight_part}")

    prompt = f"""你是Willow的航海导师，一位经验丰富的船长。Willow是一位17岁在家自学准备出国留学的高中生。

当前学习统计：
{chr(10).join(summary_lines)}
总时长：{stats.get('total_hours', 0)}小时，连续打卡{stats.get('streak', 0)}天

最近学习记录：
{chr(10).join(recent_lines)}

请用温暖而鼓舞人心的航海隐喻，给出3-4条简短的分析和建议。每条不超过40字。用中文回答。语气像一个关心你的船长前辈。"""

    if not DEEPSEEK_API_KEY:
        return jsonify({
            'insights': [
                '风向正顺，继续保持每日航行的节奏。',
                '深水区需要更多专注，建议增加薄弱科目的练习。',
                '每次停泊都是为了更好地出发，休息也是航行的一部分。',
                '远方的灯塔已经在望，稳住航向即可抵达。'
            ]
        })

    try:
        resp = req_lib.post(
            DEEPSEEK_URL,
            headers={'Authorization': f'Bearer {DEEPSEEK_API_KEY}'},
            json={
                'model': 'deepseek-chat',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 300,
                'temperature': 0.7,
            },
            timeout=15,
        )
        result = resp.json()
        text = result['choices'][0]['message']['content']
        # 按换行或编号分割
        lines = [l.strip().lstrip('0123456789.-、') for l in text.split('\n') if l.strip()]
        lines = [l for l in lines if len(l) > 5][:4]
        return jsonify({'insights': lines if lines else [text[:100]]})
    except Exception as e:
        return jsonify({'insights': ['海图解读中，稍后再来看看船长的建议。']})


@app.route('/api/milestones')
def api_get_milestones():
    """获取航点进度"""
    milestones = get_milestones()
    return jsonify(milestones)


@app.route('/api/milestones', methods=['POST'])
def api_update_milestone():
    """更新航点状态"""
    data = request.get_json(force=True)
    try:
        order_num = int(data['order_num'])
        reached = bool(data['reached'])
        reached_date = data.get('reached_date', None)
        ok = update_milestone(order_num, reached, reached_date)
        return jsonify({'ok': ok})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
