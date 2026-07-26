import os
import json
import requests
from flask import Flask, render_template, request, jsonify
from models import init_db, add_log, get_logs, get_recent_logs, get_stats

app = Flask(__name__)
init_db()

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-21b4ec37b4644a74a9a8d3bbd3c4a853")
DEEPSEEK_MODEL = "deepseek-v4-flash"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/history")
def history():
    return render_template("history.html")


@app.route("/insights")
def insights():
    return render_template("insights.html")


@app.route("/api/log", methods=["POST"])
def api_add_log():
    data = request.get_json()
    date = data.get("date")
    subject = data.get("subject", "").strip()
    duration = data.get("duration_hours", 0)
    content = data.get("content", "").strip()
    mood = data.get("mood", "").strip()

    if not subject or not content:
        return jsonify({"error": "科目和内容不能为空"}), 400

    add_log(date, subject, float(duration), content, mood)
    return jsonify({"ok": True})


@app.route("/api/logs")
def api_get_logs():
    limit = request.args.get("limit", 50, type=int)
    return jsonify(get_logs(limit))


@app.route("/api/stats")
def api_get_stats():
    return jsonify(get_stats())


@app.route("/api/insights")
def api_get_insights():
    recent = get_recent_logs(days=14)
    if not recent:
        return jsonify({"insight": "还没有学习记录，先打个卡吧！"})

    # 构建学习记录摘要
    summary_lines = []
    for r in recent:
        summary_lines.append(
            f"- {r['date']} | {r['subject']} | {r['duration_hours']}h | 心情:{r['mood']} | {r['content']}"
        )
    summary = "\n".join(summary_lines)

    prompt = f"""你是一位学习分析师。以下是用户最近的学习打卡记录：

{summary}

请基于这些数据给出一条简短的洞察（2-3句话），要求：
1. 指出具体的学习模式或趋势（哪科学得多、频率如何、时间分布等）
2. 给出一条具体的、可执行的建议（不要空洞的鼓励）
3. 语气直接，不要鸡汤"""

    try:
        resp = requests.post(
            DEEPSEEK_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
            },
            timeout=30,
        )
        resp.raise_for_status()
        insight = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        insight = f"AI 分析暂时不可用（{str(e)[:50]}），请稍后再试。"

    return jsonify({"insight": insight})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
