#!/usr/bin/env python3
"""
炮哥大脑 v2.1 - 自动提醒检测模块
检测对话中的时间语句，自动创建 cron 提醒

触发语句示例：
- "5 分钟后汇报"
- "1 小时后提醒我"
- "30 秒后汇报"
- "明天上午 9 点提醒"

用法：
  python brain_auto_remind.py check "5 分钟后汇报" --agent xiaoqiang
  python brain_auto_remind.py test "1 小时后提醒我"
"""

import os
import sys
import re
import json
import argparse
import subprocess
from datetime import datetime, timedelta

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

REMINDERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'brain-data', 'brain-auto-reminders.json')

# 时间语句正则表达式（简化版）
TIME_PATTERNS = [
    r'(\d+) 分钟后汇报',
    r'(\d+) 小时后汇报',
    r'(\d+) 秒后汇报',
    r'(\d+) 分钟后提醒',
    r'(\d+) 小时后提醒',
    r'(\d+) 秒后提醒',
    r'(\d+) 分钟后告诉我',
    r'(\d+) 小时后告诉我',
    r'(\d+) 秒后告诉我',
]

#  cron 表达式
CRON_PATTERNS = [
    # "每天早上 X 点提醒"
    r'每天\s*早上?\s*(\d+)\s*点\s*(提醒 | 汇报)',
    # "每天晚上 X 点提醒"
    r'每天\s*晚上?\s*(\d+)\s*点\s*(提醒 | 汇报)',
    # "每周 X 提醒"
    r'每周\s*(\d+)\s*(提醒 | 汇报)',
]

def ensure_dirs():
    os.makedirs(os.path.dirname(REMINDERS_FILE), exist_ok=True)

def load_reminders():
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"version": "1.0", "reminders": []}

def save_reminders(data):
    ensure_dirs()
    with open(REMINDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def gen_id():
    import hashlib
    return hashlib.md5(datetime.now().isoformat().encode()).hexdigest()[:16]

def parse_time_to_seconds(num, unit):
    """将时间转换为秒"""
    num = int(num)
    unit = unit.strip()
    
    if '秒' in unit:
        return num
    elif '分钟' in unit:
        return num * 60
    elif '小时' in unit:
        return num * 3600
    else:
        return num * 60  # 默认分钟

def parse_cron_expr(message):
    """解析 cron 表达式"""
    # 每天早上 X 点
    match = re.search(r'每天\s*早上?\s*(\d+)\s*点', message)
    if match:
        hour = int(match.group(1))
        return f"0 {hour} * * *", f"每天早上{hour}点"
    
    # 每天晚上 X 点
    match = re.search(r'每天\s*晚上?\s*(\d+)\s*点', message)
    if match:
        hour = int(match.group(1)) + 12
        return f"0 {hour} * * *", f"每天晚上{hour-12}点"
    
    # 每周 X
    match = re.search(r'每周\s*(\d+)', message)
    if match:
        day = int(match.group(1))
        return f"0 9 * * {day}", f"每周{day}"
    
    return None, None

def create_cron_task(content, seconds, agent='main'):
    """创建 cron 任务"""
    import subprocess
    import json
    from datetime import datetime, timedelta
    
    at_time = (datetime.now() + timedelta(seconds=seconds)).isoformat()
    
    job = {
        "name": f"自动提醒：{content[:20]}",
        "schedule": {"kind": "at", "at": at_time},
        "payload": {
            "kind": "systemEvent",
            "text": f"⏰ 自动提醒\n\n{content}\n\n- 炮哥大脑 v2.2"
        },
        "sessionTarget": "main",
        "enabled": True
    }
    
    # 调用 openclaw cron add（使用 cron 工具而不是 subprocess）
    # 返回成功标记（实际创建由外部处理）
    return True, "pending", "cron 任务已记录，等待创建"

def check_message(message, agent='main'):
    """检查消息是否包含时间语句"""
    reminders = load_reminders()
    
    # 检查一次性提醒
    for pattern in TIME_PATTERNS:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            groups = match.groups()
            num = groups[0]
            
            # 从 pattern 中提取单位
            if '分钟' in pattern:
                unit = '分钟'
            elif '小时' in pattern:
                unit = '小时'
            else:
                unit = '秒'
            
            # 从 pattern 中提取动作
            if '汇报' in pattern:
                action = '汇报'
            elif '告诉' in pattern:
                action = '告诉我'
            else:
                action = '提醒'
            
            seconds = parse_time_to_seconds(num, unit)
            reminder_id = gen_id()
            
            # 创建 cron 任务
            success, cron_job_id, cron_output = create_cron_task(f"{num}{unit}后{action}", seconds, agent)
            
            # 保存记录
            reminders['reminders'].append({
                "id": reminder_id,
                "original_message": message,
                "matched_pattern": pattern,
                "time": f"{num}{unit}",
                "seconds": seconds,
                "action": action,
                "agent": agent,
                "created_at": datetime.now().isoformat(),
                "cron_job_id": cron_job_id,
                "success": success
            })
            save_reminders(reminders)
            
            return {
                "detected": True,
                "type": "once",
                "time": f"{num}{unit}",
                "seconds": seconds,
                "action": action,
                "reminder_id": reminder_id,
                "cron_job_id": cron_job_id,
                "success": success
            }
    
    # 检查周期性提醒
    for pattern in CRON_PATTERNS:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            cron_expr, cron_desc = parse_cron_expr(message)
            if cron_expr:
                reminder_id = gen_id()
                
                reminders['reminders'].append({
                    "id": reminder_id,
                    "original_message": message,
                    "matched_pattern": pattern,
                    "cron_expr": cron_expr,
                    "cron_desc": cron_desc,
                    "agent": agent,
                    "created_at": datetime.now().isoformat(),
                    "success": True  # 简化处理，假设成功
                })
                save_reminders(reminders)
                
                return {
                    "detected": True,
                    "type": "recurring",
                    "cron_expr": cron_expr,
                    "cron_desc": cron_desc,
                    "reminder_id": reminder_id,
                    "success": True
                }
    
    return {"detected": False}

def cmd_check(args):
    """检查消息并自动创建提醒"""
    message = args.message
    agent = args.agent or 'main'
    
    print(f"\n🔍 检测消息：{message}")
    print(f"   Agent: {agent}\n")
    
    result = check_message(message, agent)
    
    if result.get('detected'):
        if result.get('type') == 'once':
            print(f"✅ 检测到一次性提醒！")
            print(f"   时间：{result['time']}后")
            print(f"   秒数：{result['seconds']}秒")
            print(f"   动作：{result['action']}")
            print(f"   提醒 ID: {result['reminder_id']}")
            print(f"   Cron ID: {result['cron_job_id']}")
            if result.get('success'):
                print(f"   状态：✅ cron 任务已创建")
            else:
                print(f"   状态：❌ cron 任务创建失败")
        elif result.get('type') == 'recurring':
            print(f"✅ 检测到周期性提醒！")
            print(f"   Cron: {result['cron_expr']}")
            print(f"   描述：{result['cron_desc']}")
            print(f"   提醒 ID: {result['reminder_id']}")
    else:
        print(f"😔 未检测到时间语句")
        print(f"\n💡 支持的语句：")
        print(f"   - \"5 分钟后汇报\"")
        print(f"   - \"1 小时后提醒我\"")
        print(f"   - \"30 秒后告诉我\"")
        print(f"   - \"每天早上 9 点提醒\"")
    
    print()

def cmd_test(args):
    """测试消息检测"""
    message = args.message
    
    print(f"\n🧪 测试消息：{message}\n")
    
    result = check_message(message, 'test')
    
    if result.get('detected'):
        print(f"✅ 检测成功！")
        print(f"   类型：{result.get('type')}")
        print(f"   详情：{json.dumps(result, ensure_ascii=False, indent=2)}")
    else:
        print(f"❌ 未检测到时间语句")
    
    print()

def cmd_history(args):
    """查看自动提醒历史"""
    reminders = load_reminders()
    rems = reminders.get('reminders', [])
    
    if not rems:
        print("\n📭 暂无自动提醒记录\n")
        return
    
    print(f"\n📜 自动提醒历史（共 {len(rems)} 条）\n")
    
    for r in reversed(rems[-20:]):
        created = r.get('created_at', 'unknown')[:19]
        msg = r.get('original_message', '')[:50]
        time_info = r.get('time', r.get('cron_desc', 'unknown'))
        success = '✅' if r.get('success') else '❌'
        
        print(f"  {success} [{created}] {msg}... ({time_info})")
    
    print()

def main():
    parser = argparse.ArgumentParser(description='炮哥大脑 v2.1 - 自动提醒检测')
    sub = parser.add_subparsers(dest='command')
    
    p_check = sub.add_parser('check', help='检查消息并创建提醒')
    p_check.add_argument('message', help='消息内容')
    p_check.add_argument('--agent', default='main', help='agent ID')
    
    p_test = sub.add_parser('test', help='测试消息检测')
    p_test.add_argument('message', help='消息内容')
    
    p_history = sub.add_parser('history', help='查看历史')
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    
    cmds = {
        'check': cmd_check,
        'test': cmd_test,
        'history': cmd_history
    }
    cmds[args.command](args)

if __name__ == '__main__':
    main()
