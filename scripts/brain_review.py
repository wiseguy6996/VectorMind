#!/usr/bin/env python3
"""
炮哥大脑 v2.0 - 间隔复习模块
基于克格勃遗忘曲线的记忆复习系统

用法：
  python brain_review.py check              # 检查今天需要复习的记忆
  python brain_review.py schedule --id abc123  # 查看某条记忆的复习计划
  python brain_review.py review --id abc123 --quality 5  # 标记已复习
  python brain_review.py stats              # 复习统计
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

# 克格勃遗忘曲线复习间隔（天）
# 第 1 次：1 天后，第 2 次：3 天后，第 3 次：7 天后，第 4 次：14 天后，第 5 次：30 天后
REVIEW_INTERVALS = [1, 3, 7, 14, 30, 60, 90]

EMOTION_MAP = {
    'happy': {'emoji': '😊', 'label': '开心'},
    'excited': {'emoji': '🤩', 'label': '兴奋'},
    'proud': {'emoji': '🦞', 'label': '自豪'},
    'calm': {'emoji': '😌', 'label': '平静'},
    'thoughtful': {'emoji': '🤔', 'label': '思考'},
    'determined': {'emoji': '💪', 'label': '决心'},
    'grateful': {'emoji': '💙', 'label': '感恩'},
    'creative': {'emoji': '✨', 'label': '创造'},
    'neutral': {'emoji': '📝', 'label': '普通'},
}

TYPE_MAP = {
    'decision': {'emoji': '🎯', 'label': '决策'},
    'preference': {'emoji': '❤️', 'label': '偏好'},
    'milestone': {'emoji': '🏆', 'label': '里程碑'},
    'lesson': {'emoji': '💡', 'label': '教训'},
    'idea': {'emoji': '💭', 'label': '想法'},
    'task': {'emoji': '✅', 'label': '任务'},
    'memory': {'emoji': '💙', 'label': '回忆'},
    'default': {'emoji': '📌', 'label': '记忆'},
}

BRAIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'brain-data')
DB_DIR_V2 = os.path.join(BRAIN_DIR, 'vectordb-v2')
REVIEW_FILE = os.path.join(BRAIN_DIR, 'brain-review.json')
META_FILE = os.path.join(BRAIN_DIR, 'brain-meta-v2.json')
COLLECTION_NAME = "paoge_brain_v2"

def ensure_dirs():
    os.makedirs(BRAIN_DIR, exist_ok=True)
    os.makedirs(DB_DIR_V2, exist_ok=True)

def get_client():
    if not HAS_CHROMADB:
        print("错误：需要安装 chromadb")
        sys.exit(1)
    ensure_dirs()
    return chromadb.PersistentClient(path=DB_DIR_V2)

def get_collection(client):
    return client.get_or_create_collection(name=COLLECTION_NAME)

def load_review():
    if os.path.exists(REVIEW_FILE):
        with open(REVIEW_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"version": "1.0", "reviews": {}}

def save_review(data):
    ensure_dirs()
    with open(REVIEW_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_meta():
    if os.path.exists(META_FILE):
        with open(META_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"version": "2.0", "total_stored": 0}

def save_meta(meta):
    ensure_dirs()
    with open(META_FILE, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

def gen_id(text):
    import hashlib
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:16]

def get_emotion_info(e): return EMOTION_MAP.get(e, EMOTION_MAP['neutral'])
def get_type_info(t): return TYPE_MAP.get(t, TYPE_MAP['default'])

def get_memory_by_id(client, collection, doc_id):
    results = collection.get(ids=[doc_id], include=["metadatas", "documents"])
    if results['documents'] and results['documents'][0]:
        return results['documents'][0], results['metadatas'][0]
    return None, None

def calc_next_review(review_count, last_review):
    """计算下次复习日期"""
    if review_count >= len(REVIEW_INTERVALS):
        interval = REVIEW_INTERVALS[-1]  # 使用最大间隔
    else:
        interval = REVIEW_INTERVALS[review_count]
    
    if last_review:
        last = datetime.fromisoformat(last_review)
    else:
        last = datetime.now()
    
    next_date = last + timedelta(days=interval)
    return next_date.isoformat(), interval

def render_preview(doc, meta):
    emo, typ = meta.get('emotion', 'neutral'), meta.get('type', 'default')
    tags = json.loads(meta.get('tags', '[]'))
    date = meta.get('stored_at', 'unknown')[:10]
    imp = meta.get('importance', 5)
    preview = doc[:50] + '...' if len(doc) > 50 else doc
    print(f"   {get_emotion_info(emo)['emoji']}{get_type_info(typ)['emoji']} [{date}] ⭐{imp} {preview}")
    if tags: print(f"      🏷️  {', '.join(tags)}")

def cmd_check(args):
    """检查今天需要复习的记忆"""
    client = get_client()
    collection = get_collection(client)
    review_data = load_review()
    
    today = datetime.now().date()
    due_reviews = []
    
    for doc_id, review_info in review_data.get('reviews', {}).items():
        next_review = review_info.get('next_review', '')
        if next_review:
            next_date = datetime.fromisoformat(next_review).date()
            if next_date <= today:
                doc, meta = get_memory_by_id(client, collection, doc_id)
                if doc:
                    due_reviews.append({
                        'id': doc_id,
                        'document': doc,
                        'metadata': meta,
                        'review_info': review_info,
                        'days_overdue': (today - next_date).days
                    })
    
    if not due_reviews:
        print(f"\n✅ 今天没有需要复习的记忆！")
        print(f"   好好休息，明天再来~\n")
        return
    
    print(f"\n📅 今天需要复习 {len(due_reviews)} 条记忆：\n")
    
    for i, item in enumerate(due_reviews, 1):
        review_info = item['review_info']
        review_count = review_info.get('review_count', 0)
        next_review = review_info.get('next_review', '')
        days_overdue = item['days_overdue']
        
        print(f"  [{i}] 第 {review_count + 1} 次复习", end="")
        if days_overdue > 0:
            print(f" (已逾期 {days_overdue} 天)", end="")
        print()
        render_preview(item['document'], item['metadata'])
        print(f"      📅 上次复习：{review_info.get('last_review', '未复习')}")
        print()
    
    print(f"💡 提示：使用以下命令标记复习完成：")
    print(f"   python brain_review.py review --id <ID> --quality 5\n")

def cmd_review(args):
    """标记记忆已复习"""
    client = get_client()
    collection = get_collection(client)
    review_data = load_review()
    
    doc_id = args.id
    quality = args.quality or 5  # 1-5 分，5 分最好
    
    doc, meta = get_memory_by_id(client, collection, doc_id)
    if not doc:
        print(f"😔 未找到 ID 为 {doc_id} 的记忆")
        return
    
    # 获取或创建复习记录
    if doc_id not in review_data['reviews']:
        review_data['reviews'][doc_id] = {
            'review_count': 0,
            'last_review': None,
            'next_review': None,
            'history': []
        }
    
    review_info = review_data['reviews'][doc_id]
    review_info['review_count'] = review_info.get('review_count', 0) + 1
    review_info['last_review'] = datetime.now().isoformat()
    review_info['next_review'], interval = calc_next_review(review_info['review_count'], review_info['last_review'])
    review_info['history'].append({
        'date': datetime.now().isoformat(),
        'quality': quality
    })
    
    # 保留最近 10 次历史记录
    if len(review_info['history']) > 10:
        review_info['history'] = review_info['history'][-10:]
    
    save_review(review_data)
    
    # 更新记忆的 recall_count
    new_meta = dict(meta)
    new_meta['recall_count'] = int(new_meta.get('recall_count', 0)) + 1
    collection.update(ids=[doc_id], metadatas=[new_meta])
    
    print(f"\n✅ 记忆已标记为复习完成！")
    render_preview(doc, meta)
    print(f"   复习质量：{'⭐' * quality}/5")
    print(f"   累计复习：{review_info['review_count']} 次")
    print(f"   下次复习：{review_info['next_review'][:10]} ({interval} 天后)\n")

def cmd_schedule(args):
    """查看某条记忆的复习计划"""
    client = get_client()
    collection = get_collection(client)
    review_data = load_review()
    
    doc_id = args.id
    doc, meta = get_memory_by_id(client, collection, doc_id)
    if not doc:
        print(f"😔 未找到 ID 为 {doc_id} 的记忆")
        return
    
    print(f"\n📅 复习计划：{doc[:50]}...\n")
    
    review_info = review_data['reviews'].get(doc_id)
    if not review_info:
        print("   暂无复习记录")
        print(f"\n💡 提示：这条记忆还没开始复习计划")
        print(f"   使用命令开始：python brain_review.py review --id {doc_id} --quality 5\n")
        return
    
    print(f"   累计复习：{review_info.get('review_count', 0)} 次")
    print(f"   上次复习：{review_info.get('last_review', '未复习')}")
    print(f"   下次复习：{review_info.get('next_review', '未安排')}")
    
    history = review_info.get('history', [])
    if history:
        print(f"\n   复习历史：")
        for h in history[-5:]:
            date = h.get('date', '')[:10]
            quality = h.get('quality', 5)
            print(f"      {date}: {'⭐' * quality}/5")
    
    # 显示未来复习计划
    next_review = review_info.get('next_review')
    review_count = review_info.get('review_count', 0)
    if next_review and review_count < len(REVIEW_INTERVALS):
        print(f"\n   未来计划：")
        for i in range(review_count, min(review_count + 3, len(REVIEW_INTERVALS))):
            interval = REVIEW_INTERVALS[i]
            next_date = datetime.fromisoformat(next_review) + timedelta(days=interval)
            print(f"      第 {i + 1} 次：{next_date.strftime('%Y-%m-%d')} ({interval} 天后)")
    
    print()

def cmd_stats(args):
    """复习统计"""
    review_data = load_review()
    reviews = review_data.get('reviews', {})
    
    total = len(reviews)
    if total == 0:
        print(f"\n📊 暂无复习记录\n")
        return
    
    # 统计
    total_reviews = sum(r.get('review_count', 0) for r in reviews.values())
    due_today = 0
    overdue = 0
    today = datetime.now().date()
    
    for review_info in reviews.values():
        next_review = review_info.get('next_review', '')
        if next_review:
            next_date = datetime.fromisoformat(next_review).date()
            if next_date <= today:
                due_today += 1
                if next_date < today:
                    overdue += 1
    
    # 复习分布
    review_dist = {}
    for r in reviews.values():
        cnt = r.get('review_count', 0)
        review_dist[cnt] = review_dist.get(cnt, 0) + 1
    
    print(f"\n📊 间隔复习统计")
    print(f"{'=' * 40}")
    print(f"总记忆数：{total}")
    print(f"总复习次数：{total_reviews}")
    print(f"平均复习：{total_reviews/total:.1f} 次/记忆")
    print(f"{'=' * 40}")
    print(f"今天需复习：{due_today} 条")
    print(f"已逾期：{overdue} 条")
    print(f"{'=' * 40}")
    
    if review_dist:
        print(f"\n复习次数分布：")
        for cnt in sorted(review_dist.keys()):
            print(f"   复习{cnt}次：{review_dist[cnt]} 条记忆")
    
    print(f"{'=' * 40}\n")

def cmd_init(args):
    """为所有记忆初始化复习计划"""
    client = get_client()
    collection = get_collection(client)
    review_data = load_review()
    
    all_data = collection.get(include=["metadatas", "documents"])
    if not all_data['ids']:
        print("📭 记忆库为空")
        return
    
    initialized = 0
    for doc_id in all_data['ids']:
        if doc_id not in review_data['reviews']:
            review_data['reviews'][doc_id] = {
                'review_count': 0,
                'last_review': None,
                'next_review': datetime.now().isoformat(),  # 立即可复习
                'history': []
            }
            initialized += 1
    
    save_review(review_data)
    print(f"✅ 已为 {initialized} 条记忆初始化复习计划\n")

def main():
    parser = argparse.ArgumentParser(description='炮哥大脑 v2.0 - 间隔复习模块')
    sub = parser.add_subparsers(dest='command')
    
    p_check = sub.add_parser('check', help='检查今天需要复习的记忆')
    
    p_review = sub.add_parser('review', help='标记记忆已复习')
    p_review.add_argument('--id', required=True)
    p_review.add_argument('--quality', type=int, default=5, choices=[1,2,3,4,5])
    
    p_schedule = sub.add_parser('schedule', help='查看复习计划')
    p_schedule.add_argument('--id', required=True)
    
    p_stats = sub.add_parser('stats', help='复习统计')
    
    p_init = sub.add_parser('init', help='初始化所有记忆的复习计划')
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    
    cmds = {
        'check': cmd_check,
        'review': cmd_review,
        'schedule': cmd_schedule,
        'stats': cmd_stats,
        'init': cmd_init
    }
    cmds[args.command](args)

if __name__ == '__main__':
    main()
