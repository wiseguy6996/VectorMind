#!/usr/bin/env python3
"""
炮哥大脑 v2.0 - 定时提醒模块（简化版）
直接调用 openclaw cron API

用法：
  python brain_reminder.py create "向哥哥汇报" --in 3600
  python brain_reminder.py list
  python brain_reminder.py cancel --id abc123
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

REMINDERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'brain-data', 'brain-reminders.json')

def ensure_dirs():
    os.makedirs(os.path.dirname(REMINDERS_FILE), exist_ok=True)

def load_reminders():
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"version": "1.0", "reminders": {}}

def save_reminders(data):
    ensure_dirs()
    with open(REMINDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def gen_id():
    import hashlib
    return hashlib.md5(datetime.now().isoformat().encode()).hexdigest()[:16]

def cmd_create(args):
    """创建提醒"""
    reminders = load_reminders()
    
    reminder_id = gen_id()
    content = args.content
    in_seconds = args.in_seconds
    cron_expr = args.cron
    agent = args.agent or 'main'
    
    if in_seconds:
        at_time = (datetime.now() + timedelta(seconds=in_seconds)).isoformat()
        schedule_desc = f"{in_seconds}秒后 ({at_time[:19]})"
        reminder_type = "once"
    elif cron_expr:
        schedule_desc = f"cron: {cron_expr}"
        reminder_type = "recurring"
    else:
        print("❌ 错误：需要指定 --in 或 --cron")
        print("\n💡 用法示例：")
        print("   python brain_reminder.py create \"向哥哥汇报\" --in 3600")
        print("   python brain_reminder.py create \"每日复习\" --cron \"0 9 * * *\"")
        return
    
    # 保存提醒记录
    reminders['reminders'][reminder_id] = {
        "content": content,
        "schedule": schedule_desc,
        "created_at": datetime.now().isoformat(),
        "agent": agent,
        "type": reminder_type,
        "in_seconds": in_seconds,
        "cron_expr": cron_expr
    }
    save_reminders(reminders)
    
    print(f"\n✅ 提醒已记录！")
    print(f"   ID: {reminder_id}")
    print(f"   内容：{content}")
    print(f"   时间：{schedule_desc}")
    print(f"   Agent: {agent}")
    print(f"\n⚠️  注意：需要手动创建 OpenClaw cron 任务")
    print(f"   运行以下命令：")
    
    if in_seconds:
        at_time = (datetime.now() + timedelta(seconds=in_seconds)).isoformat()
        print(f'   openclaw cron add --job \'{{"name":"提醒：{content[:20]}","schedule":{{"kind":"at","at":"{at_time}"}}, "payload":{{"kind":"systemEvent","text":"⏰ {content}"}}, "sessionTarget":"main"}}\'')
    elif cron_expr:
        print(f'   openclaw cron add --job \'{{"name":"提醒：{content[:20]}","schedule":{{"kind":"cron","expr":"{cron_expr}"}}, "payload":{{"kind":"systemEvent","text":"⏰ {content}"}}, "sessionTarget":"main"}}\'')
    
    print()

def cmd_list(args):
    """查看提醒列表"""
    reminders = load_reminders()
    rems = reminders.get('reminders', {})
    
    if not rems:
        print("\n📭 暂无提醒\n")
        return
    
    print(f"\n📋 提醒列表（共 {len(rems)} 条）\n")
    
    for rid, rinfo in rems.items():
        created = rinfo.get('created_at', 'unknown')[:19]
        schedule = rinfo.get('schedule', 'unknown')
        content = rinfo.get('content', '')[:50]
        rtype = rinfo.get('type', 'once')
        
        icon = "🔄" if rtype == "recurring" else "⏰"
        print(f"  {icon} {rid[:8]}...")
        print(f"     内容：{content}...")
        print(f"     时间：{schedule}")
        print(f"     创建：{created}")
        print()

def cmd_cancel(args):
    """取消提醒"""
    reminders = load_reminders()
    
    rid = args.id
    if rid not in reminders['reminders']:
        print(f"❌ 未找到提醒：{rid}")
        return
    
    del reminders['reminders'][rid]
    save_reminders(reminders)
    
    print(f"✅ 已取消提醒：{rid}\n")

def cmd_history(args):
    """查看历史提醒"""
    reminders = load_reminders()
    rems = reminders.get('reminders', {})
    
    if not rems:
        print("\n📭 暂无历史记录\n")
        return
    
    print(f"\n📜 历史提醒（共 {len(rems)} 条）\n")
    
    sorted_rems = sorted(rems.items(), key=lambda x: x[1].get('created_at', ''), reverse=True)
    
    for rid, rinfo in sorted_rems[:20]:
        created = rinfo.get('created_at', 'unknown')[:19]
        content = rinfo.get('content', '')[:50]
        rtype = rinfo.get('type', 'once')
        
        icon = "🔄" if rtype == "recurring" else "⏰"
        print(f"  {icon} [{created}] {content}...")
    
    print()

def main():
    parser = argparse.ArgumentParser(description='炮哥大脑 v2.0 - 定时提醒模块')
    sub = parser.add_subparsers(dest='command')
    
    p_create = sub.add_parser('create', help='创建提醒')
    p_create.add_argument('content', help='提醒内容')
    p_create.add_argument('--in', dest='in_seconds', type=int, help='多少秒后提醒')
    p_create.add_argument('--cron', help='cron 表达式')
    p_create.add_argument('--agent', default='main', help='agent ID')
    
    p_list = sub.add_parser('list', help='查看提醒列表')
    
    p_cancel = sub.add_parser('cancel', help='取消提醒')
    p_cancel.add_argument('--id', required=True)
    
    p_history = sub.add_parser('history', help='查看历史提醒')
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    
    cmds = {
        'create': cmd_create,
        'list': cmd_list,
        'cancel': cmd_cancel,
        'history': cmd_history
    }
    cmds[args.command](args)

if __name__ == '__main__':
    main()
