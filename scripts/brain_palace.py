#!/usr/bin/env python3
"""
炮哥大脑 v2.0 - 记忆宫殿导航模块
虚拟目录导航 + 多维度筛选 + 时间线浏览

用法：
  python brain_palace.py browse --tag "情绪便利店"
  python brain_palace.py browse --emotion "excited"
  python brain_palace.py browse --type "milestone"
  python brain_palace.py timeline --days 7
  python brain_palace.py tree
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from collections import defaultdict

# 修复 Windows 控制台编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

# 情感标签映射
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

# 类型映射
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

COLLECTION_NAME = "paoge_brain_v2"


def ensure_dirs():
    os.makedirs(BRAIN_DIR, exist_ok=True)
    os.makedirs(DB_DIR_V2, exist_ok=True)


def get_client():
    if not HAS_CHROMADB:
        print("错误：需要安装 chromadb。运行：pip install chromadb")
        sys.exit(1)
    ensure_dirs()
    client = chromadb.PersistentClient(path=DB_DIR_V2)
    return client


def get_collection(client):
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "炮哥大脑 v2.0 - 记忆卡片系统"}
    )


def get_emotion_info(emotion):
    return EMOTION_MAP.get(emotion, EMOTION_MAP['neutral'])


def get_type_info(mem_type):
    return TYPE_MAP.get(mem_type, TYPE_MAP['default'])


def render_memory_line(doc, metadata, index=1):
    """渲染单条记忆（简洁模式）"""
    emotion = metadata.get('emotion', 'neutral')
    mem_type = metadata.get('type', 'default')
    tags = json.loads(metadata.get('tags', '[]'))
    stored_at = metadata.get('stored_at', 'unknown')
    importance = metadata.get('importance', 5)
    
    emotion_info = get_emotion_info(emotion)
    type_info = get_type_info(mem_type)
    
    preview = doc[:50] + '...' if len(doc) > 50 else doc
    date_str = stored_at[:10] if len(stored_at) > 10 else stored_at
    
    print(f"  {index:3}. {emotion_info['emoji']}{type_info['emoji']} [{date_str}] ⭐{importance} {preview}")
    if tags:
        print(f"       🏷️  {', '.join(tags)}")


def cmd_browse(args):
    """按条件浏览记忆"""
    client = get_client()
    collection = get_collection(client)
    
    count = collection.count()
    if count == 0:
        print("📭 记忆宫殿为空")
        return
    
    # 获取所有记忆
    all_data = collection.get(include=["metadatas", "documents"], limit=args.limit or 50)
    
    filtered = []
    for doc, meta in zip(all_data['documents'], all_data['metadatas']):
        match = True
        
        # 按标签筛选
        if args.tag:
            tags = json.loads(meta.get('tags', '[]'))
            if not any(args.tag.lower() in t.lower() for t in tags):
                match = False
        
        # 按情感筛选
        if args.emotion:
            if meta.get('emotion', 'neutral') != args.emotion:
                match = False
        
        # 按类型筛选
        if args.type:
            if meta.get('type', 'default') != args.type:
                match = False
        
        # 按重要度筛选
        if args.min_importance:
            if meta.get('importance', 5) < args.min_importance:
                match = False
        
        if match:
            filtered.append((doc, meta))
    
    if not filtered:
        print(f"🔍 没有找到符合条件的记忆")
        if args.tag:
            print(f"   标签：{args.tag}")
        if args.emotion:
            info = get_emotion_info(args.emotion)
            print(f"   情感：{info['emoji']} {info['label']}")
        if args.type:
            info = get_type_info(args.type)
            print(f"   类型：{info['emoji']} {info['label']}")
        return
    
    # 显示结果
    print(f"\n🏛️  记忆宫殿 - 浏览结果（共 {len(filtered)} 条）\n")
    
    for i, (doc, meta) in enumerate(filtered, 1):
        render_memory_line(doc, meta, index=i)
    
    print()


def cmd_timeline(args):
    """时间线浏览"""
    client = get_client()
    collection = get_collection(client)
    
    count = collection.count()
    if count == 0:
        print("📭 记忆宫殿为空")
        return
    
    # 获取所有记忆
    all_data = collection.get(include=["metadatas", "documents"], limit=args.limit or 100)
    
    # 按日期分组
    days = args.days or 7
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    memories_by_date = defaultdict(list)
    for doc, meta in zip(all_data['documents'], all_data['metadatas']):
        stored_at = meta.get('stored_at', '')
        if stored_at >= cutoff:
            date_key = stored_at[:10]  # YYYY-MM-DD
            memories_by_date[date_key].append((doc, meta))
    
    if not memories_by_date:
        print(f"📅 过去 {days} 天没有记忆")
        return
    
    print(f"\n🕐 记忆宫殿 - 时间线（过去 {days} 天）\n")
    
    # 按日期倒序显示
    for date in sorted(memories_by_date.keys(), reverse=True):
        memories = memories_by_date[date]
        print(f"📅 {date} ({len(memories)} 条)")
        for i, (doc, meta) in enumerate(memories, 1):
            render_memory_line(doc, meta, index=i)
        print()


def cmd_tree(args):
    """层级目录树"""
    client = get_client()
    collection = get_collection(client)
    
    count = collection.count()
    if count == 0:
        print("📭 记忆宫殿为空")
        return
    
    # 获取所有记忆
    all_data = collection.get(include=["metadatas", "documents"], limit=args.limit or 100)
    
    # 按标签分组
    tag_memories = defaultdict(list)
    untagged = []
    
    for doc, meta in zip(all_data['documents'], all_data['metadatas']):
        tags = json.loads(meta.get('tags', '[]'))
        if tags:
            for tag in tags:
                tag_memories[tag].append((doc, meta))
        else:
            untagged.append((doc, meta))
    
    print(f"\n🏛️  记忆宫殿 - 目录树（共 {count} 条记忆）\n")
    
    # 显示标签目录
    if tag_memories:
        print("📁 标签目录")
        for tag in sorted(tag_memories.keys()):
            memories = tag_memories[tag]
            print(f"  📂 {tag} ({len(memories)} 条)")
            for doc, meta in memories[:5]:  # 每个标签最多显示 5 条
                emotion = meta.get('emotion', 'neutral')
                emotion_info = get_emotion_info(emotion)
                preview = doc[:40] + '...' if len(doc) > 40 else doc
                print(f"     {emotion_info['emoji']} {preview}")
            if len(memories) > 5:
                print(f"     ... 还有 {len(memories) - 5} 条")
        print()
    
    # 显示未分类记忆
    if untagged:
        print(f"📁 未分类 ({len(untagged)} 条)")
        for doc, meta in untagged[:5]:
            emotion = meta.get('emotion', 'neutral')
            emotion_info = get_emotion_info(emotion)
            preview = doc[:40] + '...' if len(doc) > 40 else doc
            print(f"   {emotion_info['emoji']} {preview}")
        if len(untagged) > 5:
            print(f"   ... 还有 {len(untagged) - 5} 条")
    
    print()


def cmd_emotions(args):
    """按情感分组浏览"""
    client = get_client()
    collection = get_collection(client)
    
    count = collection.count()
    if count == 0:
        print("📭 记忆宫殿为空")
        return
    
    # 获取所有记忆
    all_data = collection.get(include=["metadatas", "documents"], limit=args.limit or 100)
    
    # 按情感分组
    emotion_memories = defaultdict(list)
    for doc, meta in zip(all_data['documents'], all_data['metadatas']):
        emotion = meta.get('emotion', 'neutral')
        emotion_memories[emotion].append((doc, meta))
    
    print(f"\n🎨 记忆宫殿 - 情感分组（共 {count} 条记忆）\n")
    
    # 按数量倒序显示
    for emotion in sorted(emotion_memories.keys(), key=lambda e: -len(emotion_memories[e])):
        memories = emotion_memories[emotion]
        info = get_emotion_info(emotion)
        print(f"{info['emoji']} {info['label']} ({len(memories)} 条)")
        for doc, meta in memories[:3]:  # 每个情感最多显示 3 条
            preview = doc[:50] + '...' if len(doc) > 50 else doc
            print(f"   • {preview}")
        if len(memories) > 3:
            print(f"   ... 还有 {len(memories) - 3} 条")
        print()


def cmd_types(args):
    """按类型分组浏览"""
    client = get_client()
    collection = get_collection(client)
    
    count = collection.count()
    if count == 0:
        print("📭 记忆宫殿为空")
        return
    
    # 获取所有记忆
    all_data = collection.get(include=["metadatas", "documents"], limit=args.limit or 100)
    
    # 按类型分组
    type_memories = defaultdict(list)
    for doc, meta in zip(all_data['documents'], all_data['metadatas']):
        mem_type = meta.get('type', 'default')
        type_memories[mem_type].append((doc, meta))
    
    print(f"\n📌 记忆宫殿 - 类型分组（共 {count} 条记忆）\n")
    
    # 按数量倒序显示
    for mem_type in sorted(type_memories.keys(), key=lambda t: -len(type_memories[t])):
        memories = type_memories[mem_type]
        info = get_type_info(mem_type)
        print(f"{info['emoji']} {info['label']} ({len(memories)} 条)")
        for doc, meta in memories[:3]:  # 每个类型最多显示 3 条
            preview = doc[:50] + '...' if len(doc) > 50 else doc
            print(f"   • {preview}")
        if len(memories) > 3:
            print(f"   ... 还有 {len(memories) - 3} 条")
        print()


def cmd_tags(args):
    """列出所有标签"""
    client = get_client()
    collection = get_collection(client)
    
    count = collection.count()
    if count == 0:
        print("📭 记忆宫殿为空")
        return
    
    # 获取所有记忆
    all_data = collection.get(include=["metadatas"], limit=args.limit or 100)
    
    # 统计标签
    tag_count = defaultdict(int)
    for meta in all_data['metadatas']:
        tags = json.loads(meta.get('tags', '[]'))
        for tag in tags:
            tag_count[tag] += 1
    
    if not tag_count:
        print("🏷️  没有标签")
        return
    
    print(f"\n🏷️  记忆宫殿 - 标签云（共 {len(tag_count)} 个标签）\n")
    
    # 按数量倒序显示
    for tag in sorted(tag_count.keys(), key=lambda t: -tag_count[t]):
        count = tag_count[tag]
        print(f"  📂 {tag}: {count} 条")
    
    print()


def main():
    parser = argparse.ArgumentParser(description='炮哥大脑 v2.0 - 记忆宫殿导航')
    subparsers = parser.add_subparsers(dest='command', help='命令')

    # browse - 按条件浏览
    p_browse = subparsers.add_parser('browse', help='按条件浏览记忆')
    p_browse.add_argument('--tag', help='按标签筛选')
    p_browse.add_argument('--emotion', help='按情感筛选', choices=list(EMOTION_MAP.keys()))
    p_browse.add_argument('--type', help='按类型筛选', choices=list(TYPE_MAP.keys()))
    p_browse.add_argument('--min-importance', type=int, help='最小重要度')
    p_browse.add_argument('--limit', type=int, default=50, help='显示条数')

    # timeline - 时间线
    p_timeline = subparsers.add_parser('timeline', help='时间线浏览')
    p_timeline.add_argument('--days', type=int, default=7, help='过去多少天')
    p_timeline.add_argument('--limit', type=int, default=100, help='显示条数')

    # tree - 目录树
    p_tree = subparsers.add_parser('tree', help='层级目录树')
    p_tree.add_argument('--limit', type=int, default=100, help='显示条数')

    # emotions - 情感分组
    p_emotions = subparsers.add_parser('emotions', help='按情感分组浏览')
    p_emotions.add_argument('--limit', type=int, default=100, help='显示条数')

    # types - 类型分组
    p_types = subparsers.add_parser('types', help='按类型分组浏览')
    p_types.add_argument('--limit', type=int, default=100, help='显示条数')

    # tags - 标签云
    p_tags = subparsers.add_parser('tags', help='列出所有标签')
    p_tags.add_argument('--limit', type=int, default=100, help='显示条数')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        'browse': cmd_browse,
        'timeline': cmd_timeline,
        'tree': cmd_tree,
        'emotions': cmd_emotions,
        'types': cmd_types,
        'tags': cmd_tags,
    }

    commands[args.command](args)


if __name__ == '__main__':
    main()
