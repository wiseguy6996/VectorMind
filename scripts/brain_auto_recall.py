#!/usr/bin/env python3
"""
炮哥大脑 v2.2 - 会话开始自动检索
每次会话开始时自动检索关键记忆，防止跨会话失忆

触发语句：
- 会话开始时自动运行
- 或手动运行：python brain_auto_recall.py

检索内容：
1. 三人团信息（小强、哥哥、炮哥）
2. 当前项目进度
3. 用户偏好
4. 最近的重要记忆
"""

import os
import sys
import subprocess
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BRAIN_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BRAIN_PY = os.path.join(BRAIN_SCRIPTS_DIR, 'brain.py')

# 关键检索词列表（每次会话开始自动检索）
KEY_RECALLS = [
    {"query": "三人团", "desc": "👨‍👨‍👦 三人团成员信息"},
    {"query": "小强", "desc": "🐛 小强（首席工程师）"},
    {"query": "wiseguy 哥哥", "desc": "💙 哥哥（用户）信息"},
    {"query": "正在进行的项目", "desc": "🎯 当前项目进度"},
    {"query": "用户偏好 视频比例", "desc": "❤️ 用户偏好设置"},
]

# 检索条数
N_RESULTS = 3


def run_recall(query, n=N_RESULTS):
    """运行 brain.py recall 命令"""
    cmd = [sys.executable, BRAIN_PY, 'recall', query, '-n', str(n)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8')
        return result.stdout, result.returncode
    except Exception as e:
        return f"错误：{e}", -1


def main():
    print(f"\n{'=' * 60}")
    print(f"🧠 炮哥大脑 v2.2 - 会话开始自动检索")
    print(f"{'=' * 60}")
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}\n")

    # 检查 brain.py 是否存在
    if not os.path.exists(BRAIN_PY):
        print(f"❌ 未找到 brain.py: {BRAIN_PY}")
        print(f"   请确保炮哥大脑 v1.0 已安装")
        return

    # 检查记忆库是否有内容
    cmd = [sys.executable, BRAIN_PY, 'stats']
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8')
    if '总记忆数：0' in result.stdout or '未找到' in result.stdout:
        print(f"📭 记忆库为空，跳过自动检索")
        print(f"   请先使用 brain.py store 存入记忆")
        return

    # 逐个检索关键记忆
    for item in KEY_RECALLS:
        query = item['query']
        desc = item['desc']
        
        print(f"\n{desc}")
        print(f"   检索：\"{query}\"")
        print(f"{'-' * 40}")
        
        stdout, code = run_recall(query)
        
        if code == 0 and '找到 0 条' not in stdout:
            # 只显示前 3 条结果（简化输出）
            lines = stdout.strip().split('\n')
            for line in lines[:10]:  # 限制输出行数
                print(f"   {line}")
            if len(lines) > 10:
                print(f"   ... (还有更多结果)")
        else:
            print(f"   📭 没有找到相关记忆")
    
    print(f"\n{'=' * 60}")
    print(f"✅ 自动检索完成！")
    print(f"{'=' * 60}\n")


if __name__ == '__main__':
    main()
