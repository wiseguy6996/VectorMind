#!/usr/env python3
"""
炮哥大脑 v2.0 - 记忆卡片 UI 模块
emoji + 情感标签 + 卡片式展示

用法：
  python brain_card.py store "今天完成了情绪便利店文案库！" --emotion happy
  python brain_card.py recall "情绪便利店"
  python brain_card.py show --id abc123
"""

import os
import sys
import json
import argparse
from datetime import datetime

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
    'happy': {'emoji': '😊', 'color': '🟡', 'label': '开心'},
    'excited': {'emoji': '🤩', 'color': '🟠', 'label': '兴奋'},
    'proud': {'emoji': '🦞', 'color': '🔴', 'label': '自豪'},
    'calm': {'emoji': '😌', 'color': '🔵', 'label': '平静'},
    'thoughtful': {'emoji': '🤔', 'color': '🟣', 'label': '思考'},
    'determined': {'emoji': '💪', 'color': '🟢', 'label': '决心'},
    'grateful': {'emoji': '💙', 'color': '🔵', 'label': '感恩'},
    'creative': {'emoji': '✨', 'color': '🟡', 'label': '创造'},
    'neutral': {'emoji': '📝', 'color': '⚪', 'label': '普通'},
}

# 记忆类型映射
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
DB_DIR = os.path.join(BRAIN_DIR, 'vectordb')
DB_DIR_V2 = os.path.join(BRAIN_DIR, 'vectordb-v2')
META_FILE = os.path.join(BRAIN_DIR, 'brain-meta-v2.json')

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


def load_meta():
    if os.path.exists(META_FILE):
        with open(META_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"version": "2.0", "total_stored": 0, "total_recalled": 0, "created": datetime.now().isoformat()}


def save_meta(meta):
    ensure_dirs()
    with open(META_FILE, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def gen_id(text):
    import hashlib
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:16]


def get_emotion_info(emotion):
    """获取情感信息"""
    return EMOTION_MAP.get(emotion, EMOTION_MAP['neutral'])


def get_type_info(mem_type):
    """获取类型信息"""
    return TYPE_MAP.get(mem_type, TYPE_MAP['default'])


def render_card(doc, metadata, index=1, show_distance=False, distance=0):
    """渲染记忆卡片"""
    emotion = metadata.get('emotion', 'neutral')
    mem_type = metadata.get('type', 'default')
    tags = json.loads(metadata.get('tags', '[]'))
    importance = metadata.get('importance', 5)
    stored_at = metadata.get('stored_at', 'unknown')
    recall_count = metadata.get('recall_count', 0)
    
    emotion_info = get_emotion_info(emotion)
    type_info = get_type_info(mem_type)
    
    # 计算相关度
    if show_distance:
        relevance = max(0, round((1 - distance / 2) * 100, 1))
    else:
        relevance = 100.0
    
    # 渲染卡片
    print(f"╔══════════════════════════════════════════════════════════╗")
    print(f"║  {emotion_info['emoji']} {type_info['emoji']} 记忆卡片 #{index:03d}")
    print(f"╠══════════════════════════════════════════════════════════╣")
    print(f"║  📌 内容：")
    
    # 内容换行处理（每行最多 50 字符）
    lines = []
    for i in range(0, len(doc), 50):
        lines.append(doc[i:i+50])
    for line in lines:
        print(f"║     {line:<50}")
    
    print(f"╠══════════════════════════════════════════════════════════╣")
    print(f"║  🏷️  情感：{emotion_info['emoji']} {emotion_info['label']:<10} 类型：{type_info['emoji']} {type_info['label']}")
    print(f"║  📊 重要度：{'⭐' * importance}{'☆' * (10-importance)} ({importance}/10)")
    print(f"║  🏷️  标签：{', '.join(tags) if tags else '无'}")
    print(f"║  📅 存入：{stored_at[:10]} {stored_at[11:19] if len(stored_at) > 11 else ''}")
    print(f"║  👁️ 被检索：{recall_count} 次")
    if show_distance:
        print(f"║  🔍 相关度：{relevance}%")
    print(f"╚══════════════════════════════════════════════════════════╝")
    print()


def cmd_store(args):
    """存入记忆卡片"""
    client = get_client()
    collection = get_collection(client)
    meta = load_meta()

    text = args.text
    emotion = args.emotion or 'neutral'
    mem_type = args.type or 'default'
    tags = args.tags.split(',') if args.tags else []
    importance = args.importance or 5

    doc_id = gen_id(text + datetime.now().isoformat())

    metadata = {
        "emotion": emotion,
        "type": mem_type,
        "tags": json.dumps(tags, ensure_ascii=False),
        "importance": importance,
        "recall_count": 0,
        "stored_at": datetime.now().isoformat(),
        "last_recalled": "",
    }

    collection.add(
        documents=[text],
        metadatas=[metadata],
        ids=[doc_id]
    )

    meta["total_stored"] = meta.get("total_stored", 0) + 1
    save_meta(meta)

    # 渲染卡片
    emotion_info = get_emotion_info(emotion)
    type_info = get_type_info(mem_type)
    
    print(f"\n{emotion_info['emoji']} 记忆卡片已存入！")
    print(f"   内容：{text[:60]}{'...' if len(text) > 60 else ''}")
    print(f"   情感：{emotion_info['emoji']} {emotion_info['label']}")
    print(f"   类型：{type_info['emoji']} {type_info['label']}")
    print(f"   标签：{tags}")
    print(f"   重要度：{importance}/10")
    print(f"   ID: {doc_id}\n")


def cmd_recall(args):
    """检索记忆卡片"""
    client = get_client()
    collection = get_collection(client)
    meta = load_meta()

    query = args.query
    n = args.n or 5

    results = collection.query(
        query_texts=[query],
        n_results=min(n, collection.count()) if collection.count() > 0 else 1
    )

    if not results['documents'] or not results['documents'][0]:
        print(f"😔 未找到与 '{query}' 相关的记忆")
        return

    meta["total_recalled"] = meta.get("total_recalled", 0) + 1
    save_meta(meta)

    print(f"\n🧠 搜索：\"{query}\"\n")

    for i, (doc, meta_item, distance) in enumerate(zip(
        results['documents'][0],
        results['metadatas'][0],
        results['distances'][0]
    ), 1):
        render_card(doc, meta_item, index=i, show_distance=True, distance=distance)

        # 更新 recall_count
        doc_id = results['ids'][0][i-1]
        new_meta = dict(meta_item)
        new_meta['recall_count'] = int(new_meta.get('recall_count', 0)) + 1
        new_meta['last_recalled'] = datetime.now().isoformat()
        collection.update(ids=[doc_id], metadatas=[new_meta])


def cmd_show(args):
    """显示单张记忆卡片"""
    client = get_client()
    collection = get_collection(client)

    doc_id = args.id

    results = collection.get(ids=[doc_id], include=["metadatas", "documents"])

    if not results['documents'] or not results['documents'][0]:
        print(f"😔 未找到 ID 为 {doc_id} 的记忆")
        return

    doc = results['documents'][0]
    meta_item = results['metadatas'][0]

    render_card(doc, meta_item, index=1)


def cmd_list(args):
    """列出所有记忆卡片"""
    client = get_client()
    collection = get_collection(client)

    count = collection.count()
    if count == 0:
        print("📭 记忆库为空")
        return

    print(f"\n🧠 炮哥大脑 v2.0 - 记忆卡片列表（共 {count} 条）\n")

    all_data = collection.get(include=["metadatas", "documents"], limit=args.limit or 20)

    for i, (doc, meta_item) in enumerate(zip(all_data['documents'], all_data['metadatas']), 1):
        emotion = meta_item.get('emotion', 'neutral')
        emotion_info = get_emotion_info(emotion)
        preview = doc[:40] + '...' if len(doc) > 40 else doc
        stored_at = meta_item.get('stored_at', 'unknown')[:10]
        
        print(f"{i:3}. {emotion_info['emoji']} [{stored_at}] {preview}")

    print()


def cmd_stats(args):
    """统计信息"""
    client = get_client()
    collection = get_collection(client)
    meta = load_meta()

    count = collection.count()

    print(f"\n🧠 炮哥大脑 v2.0 - 记忆卡片系统统计")
    print(f"{'=' * 50}")
    print(f"总记忆数：{count}")
    print(f"累计存入：{meta.get('total_stored', 0)}")
    print(f"累计检索：{meta.get('total_recalled', 0)}")
    print(f"创建时间：{meta.get('created', 'unknown')[:10]}")
    print(f"数据目录：{DB_DIR_V2}")
    print(f"{'=' * 50}")

    if count > 0:
        all_data = collection.get(include=["metadatas"])
        
        # 情感分布
        emotions = {}
        for m in all_data['metadatas']:
            e = m.get('emotion', 'neutral')
            emotions[e] = emotions.get(e, 0) + 1
        
        print(f"\n🎨 情感分布：")
        for emo, cnt in sorted(emotions.items(), key=lambda x: -x[1]):
            info = get_emotion_info(emo)
            print(f"   {info['emoji']} {info['label']}: {cnt} 条")
        
        # 类型分布
        types = {}
        for m in all_data['metadatas']:
            t = m.get('type', 'default')
            types[t] = types.get(t, 0) + 1
        
        print(f"\n📌 类型分布：")
        for t, cnt in sorted(types.items(), key=lambda x: -x[1]):
            info = get_type_info(t)
            print(f"   {info['emoji']} {info['label']}: {cnt} 条")
        
        print(f"{'=' * 50}")


def main():
    parser = argparse.ArgumentParser(description='炮哥大脑 v2.0 - 记忆卡片 UI')
    subparsers = parser.add_subparsers(dest='command', help='命令')

    # store
    p_store = subparsers.add_parser('store', help='存入记忆卡片')
    p_store.add_argument('text', help='记忆内容')
    p_store.add_argument('--emotion', default='neutral', 
                        choices=list(EMOTION_MAP.keys()),
                        help='情感标签')
    p_store.add_argument('--type', default='default',
                        choices=list(TYPE_MAP.keys()),
                        help='记忆类型')
    p_store.add_argument('--tags', default='', help='标签（逗号分隔）')
    p_store.add_argument('--importance', type=int, default=5, help='重要度 1-10')

    # recall
    p_recall = subparsers.add_parser('recall', help='检索记忆卡片')
    p_recall.add_argument('query', help='搜索关键词')
    p_recall.add_argument('-n', type=int, default=5, help='返回条数')

    # show
    p_show = subparsers.add_parser('show', help='显示单张卡片')
    p_show.add_argument('--id', required=True, help='记忆 ID')

    # list
    p_list = subparsers.add_parser('list', help='列出记忆卡片')
    p_list.add_argument('--limit', type=int, default=20, help='显示条数')

    # stats
    subparsers.add_parser('stats', help='统计信息')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        'store': cmd_store,
        'recall': cmd_recall,
        'show': cmd_show,
        'list': cmd_list,
        'stats': cmd_stats,
    }

    commands[args.command](args)


if __name__ == '__main__':
    main()
