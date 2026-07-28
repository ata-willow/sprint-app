"""Sprint - 航海主题学习打卡 PWA"""
import os
import json
from datetime import datetime
import requests as req_lib
from flask import Flask, render_template, request, jsonify
from models import (init_db, add_log, get_logs, get_stats, get_milestones,
                    update_milestone, add_mock_score, get_mock_scores,
                    get_subject_predictions, get_yearly_heatmap, get_timeline)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

DEEPSEEK_API_KEY = 'sk21b4ec37b4644a74a9a8d3bbd3c4a853'
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


def _get_latest_reached_order(milestones):
    """获取最新到达的里程碑的order_num"""
    latest = 0
    for m in milestones:
        if m['reached']:
            latest = m['order_num']
    return latest


@app.route('/')
def index():
    """航海页（首页）"""
    milestones = _mark_current_milestone(get_milestones())
    stats = get_stats()
    predictions = get_subject_predictions()
    latest_reached = _get_latest_reached_order(milestones)
    return render_template('index.html', milestones=milestones, stats=stats,
                           predictions=predictions, latest_reached=latest_reached)


@app.route('/log')
def log_page():
    """日志页"""
    logs = get_logs(limit=30)
    stats = get_stats()
    mock_scores = get_mock_scores(limit=20)
    return render_template('log.html', logs=logs, insights=stats.get('insights', []), mock_scores=mock_scores)


@app.route('/route')
def route_page():
    """航线页"""
    milestones = _mark_current_milestone(get_milestones())
    stats = get_stats()
    timeline = get_timeline(limit=30)
    return render_template('route.html', milestones=milestones, stats=stats, timeline=timeline)


@app.route('/review')
def review_page():
    """复盘页"""
    stats = get_stats()
    return render_template('review.html', stats=stats)


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
            unit=data.get('unit', None),
            log_type=data.get('log_type', 'study'),
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


@app.route('/api/mock-scores', methods=['POST'])
def api_add_mock_score():
    """添加模考分数"""
    data = request.get_json(force=True)
    try:
        score_id = add_mock_score(
            subject=data['subject'],
            score=float(data['score']),
            date=data.get('date', datetime.now().strftime('%Y-%m-%d')),
            exam_name=data.get('exam_name', None),
        )
        return jsonify({'ok': True, 'id': score_id})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@app.route('/api/mock-scores')
def api_get_mock_scores():
    """获取模考分数列表"""
    subject = request.args.get('subject', None)
    limit = request.args.get('limit', 30, type=int)
    scores = get_mock_scores(subject=subject, limit=limit)
    return jsonify(scores)


@app.route('/api/predictions')
def api_get_predictions():
    """获取学科预测分"""
    predictions = get_subject_predictions()
    return jsonify(predictions)


@app.route('/api/yearly-heatmap')
def api_yearly_heatmap():
    """获取年度热力图数据"""
    year = request.args.get('year', datetime.now().year, type=int)
    data = get_yearly_heatmap(year)
    return jsonify(data)


@app.route('/api/timeline')
def api_get_timeline():
    """获取混合时间线"""
    limit = request.args.get('limit', 30, type=int)
    timeline = get_timeline(limit=limit)
    return jsonify(timeline)


@app.route('/api/monthly-review', methods=['POST'])
def api_monthly_review():
    """AI月度复盘"""
    data = request.get_json(force=True)
    month = data.get('month', datetime.now().strftime('%Y-%m'))

    logs = get_logs(limit=200)
    month_logs = [l for l in logs if l['date'].startswith(month)]

    mock_scores = get_mock_scores(limit=100)
    month_scores = [s for s in mock_scores if s['date'].startswith(month)]

    study_days = len(set(l['date'] for l in month_logs))
    total_hours = sum(l['duration_hours'] for l in month_logs)

    if not month_logs and not month_scores:
        return jsonify({'review': '这个月还没有学习记录，开始你的航程吧！⚓'})

    log_lines = []
    for l in month_logs[:30]:
        unit_part = f" [{l.get('unit', '')}]" if l.get('unit') else ''
        log_lines.append(f"  {l['date']}{unit_part} {l['subject']} {l['duration_hours']}h 心情{l.get('mood', '?')}")

    score_lines = []
    for s in month_scores:
        exam_part = f" ({s.get('exam_name', '')})" if s.get('exam_name') else ''
        score_lines.append(f"  {s['date']}{exam_part} {s['subject']} {s['score']}分")

    prompt = f"""你是陪伴学习者的顾问，阅读学习日志、模考记录，写下简短评语。

请为Willow（17岁，在家自学准备出国留学的高中生）生成{month}月的学习复盘。

本月数据：
- 学习天数：{study_days}天
- 总学习时长：{round(total_hours, 1)}小时
- 平均每日：{round(total_hours / max(study_days, 1), 1)}小时

学习记录：
{chr(10).join(log_lines)}

模考分数：
{chr(10).join(score_lines) if score_lines else '  本月暂无模考'}

请严格按以下JSON格式返回（不要加markdown代码块标记，直接返回纯JSON）：
{{
  "mood": "一个最能代表本月学习状态的emoji",
  "title": "一句话概括这个月（10字以内）",
  "summary": "整体回顾，2-3句话",
  "highlights": ["亮点1（一句话）", "亮点2"],
  "improvements": ["建议1（一句话）", "建议2"],
  "next_month": "下个月的一句话方向"
}}

要求：
1. 语言平实克制，去掉所有比喻和宏大叙事，纯粹围绕学习本身
2. 带有温和的温度，不冰冷生硬，拒绝空洞鸡汤
3. 立足当下成绩与记录内容，客观点评，只做总结和提点
4. 不要强行安排学习计划
5. highlights和improvements各2-3条，每条一句话"""

    if not DEEPSEEK_API_KEY:
        import json as _json
        fallback = {
            "mood": "🌱",
            "title": "蓄势待发",
            "summary": f"本月学习了{study_days}天，累计{round(total_hours, 1)}小时。好的开始是成功的一半。",
            "highlights": ["保持了每日学习的习惯", "开始了新的学习旅程"],
            "improvements": ["可以尝试增加单科深度", "模考数据会帮助更精准地定位薄弱点"],
            "next_month": "继续积累，建立稳定的学习节奏"
        }
        return jsonify({'review': _json.dumps(fallback, ensure_ascii=False)})

    try:
        resp = req_lib.post(
            DEEPSEEK_URL,
            headers={'Authorization': f'Bearer {DEEPSEEK_API_KEY}'},
            json={
                'model': 'deepseek-chat',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 600,
                'temperature': 0.7,
            },
            timeout=20,
        )
        result = resp.json()
        text = result['choices'][0]['message']['content']
        return jsonify({'review': text})
    except Exception as e:
        import json as _json
        fallback = {
            "mood": "⏳",
            "title": "稍后再试",
            "summary": "复盘生成遇到了一点问题，请稍后重试。",
            "highlights": [],
            "improvements": [],
            "next_month": ""
        }
        return jsonify({'review': _json.dumps(fallback, ensure_ascii=False)})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
