#!/usr/bin/env python3
"""
炮哥大脑 v2.0 - 关联记忆模块
新记忆自动链接旧记忆，形成记忆网络

用法：
  python brain_link.py store "情绪便利店本周上线" --auto-link
  python brain_link.py links --id abc123
  python brain_link.py link --id1 abc123 --id2 def456
  python brain_link.py unlink --id1 abc123 --id2 def456
"""

import os
import sys
import json
import argparse
from datetime import datetime
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

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
LINKS_FILE = os.path.join(BRAIN_DIR, 'brain-links.json')
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

def load_links():
    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"version": "1.0", "links": {}}

def save_links(data):
    ensure_dirs()
    with open(LINKS_FILE, 'w', encoding='utf-8') as f:
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

def find_related(client, collection, text, n=5, exclude_id=None):
    results = collection.query(query_texts=[text], n_results=n)
    related = []
    if results['documents'] and results['documents'][0]:
        for doc, meta, dist, did in zip(results['documents'][0], results['metadatas'][0], results['distances'][0], results['ids'][0]):
            if exclude_id and did == exclude_id: continue
            rel = max(0, round((1 - dist / 2) * 100, 1))
            if rel > 30:
                related.append({'id': did, 'document': doc, 'metadata': meta, 'relevance': rel})
    return related

def render_preview(doc, meta, rel=None):
    emo, typ = meta.get('emotion', 'neutral'), meta.get('type', 'default')
    tags = json.loads(meta.get('tags', '[]'))
    date = meta.get('stored_at', 'unknown')[:10]
    imp = meta.get('importance', 5)
    preview = doc[:50] + '...' if len(doc) > 50 else doc
    line = f"   {get_emotion_info(emo)['emoji']}{get_type_info(typ)['emoji']} [{date}] ⭐{imp} {preview}"
    if rel: line += f" (相关度：{rel}%)"
    print(line)
    if tags: print(f"      🏷️  {', '.join(tags)}")

def cmd_store(args):
    client = get_client()
    collection = get_collection(client)
    meta = load_meta()
    links_data = load_links()
    
    text, emo, typ = args.text, args.emotion or 'neutral', args.type or 'default'
    tags = args.tags.split(',') if args.tags else []
    imp = args.importance or 5
    
    doc_id = gen_id(text + datetime.now().isoformat())
    metadata = {"emotion": emo, "type": typ, "tags": json.dumps(tags, ensure_ascii=False),
                "importance": imp, "recall_count": 0, "stored_at": datetime.now().isoformat()}
    
    collection.add(documents=[text], metadatas=[metadata], ids=[doc_id])
    meta["total_stored"] = meta.get("total_stored", 0) + 1
    save_meta(meta)
    
    print(f"\n{get_emotion_info(emo)['emoji']} 记忆卡片已存入！")
    print(f"   内容：{text[:60]}{'...' if len(text) > 60 else ''}")
    print(f"   情感：{get_emotion_info(emo)['emoji']} {get_emotion_info(emo)['label']}")
    print(f"   类型：{get_type_info(typ)['emoji']} {get_type_info(typ)['label']}")
    print(f"   标签：{tags}, 重要度：{imp}/10, ID: {doc_id}")
    
    if args.auto_link:
        print(f"\n🔗 正在查找关联记忆...")
        related = find_related(client, collection, text, n=5, exclude_id=doc_id)
        if related:
            print(f"\n🔗 发现 {len(related)} 条关联记忆：\n")
            auto_linked = 0
            for i, item in enumerate(related, 1):
                print(f"  [{i}] 相关度：{item['relevance']}%")
                render_preview(item['document'], item['metadata'])
                if item['relevance'] > 50:
                    links_data['links'].setdefault(doc_id, []).append(item['id'])
                    links_data['links'].setdefault(item['id'], []).append(doc_id)
                    auto_linked += 1
            save_links(links_data)
            print(f"\n✅ 已自动建立 {auto_linked} 条强关联")
        else:
            print(f"\n😔 没有找到关联记忆")
    print()

def cmd_links(args):
    client = get_client()
    collection = get_collection(client)
    links_data = load_links()
    doc, meta = get_memory_by_id(client, collection, args.id)
    if not doc:
        print(f"😔 未找到 ID 为 {args.id} 的记忆")
        return
    print(f"\n🔗 记忆关联：{doc[:50]}...\n")
    linked_ids = links_data['links'].get(args.id, [])
    if not linked_ids:
        print("   没有关联记忆")
        return
    print(f"   共 {len(linked_ids)} 条关联：\n")
    for i, lid in enumerate(linked_ids, 1):
        ldoc, lmeta = get_memory_by_id(client, collection, lid)
        if ldoc:
            print(f"  [{i}]")
            render_preview(ldoc, lmeta)
            print()

def cmd_link(args):
    links_data = load_links()
    links_data['links'].setdefault(args.id1, []).append(args.id2)
    links_data['links'].setdefault(args.id2, []).append(args.id1)
    save_links(links_data)
    print(f"✅ 已建立关联：{args.id1} ↔ {args.id2}\n")

def cmd_unlink(args):
    links_data = load_links()
    if args.id1 in links_data['links'] and args.id2 in links_data['links'][args.id1]:
        links_data['links'][args.id1].remove(args.id2)
    if args.id2 in links_data['links'] and args.id1 in links_data['links'][args.id2]:
        links_data['links'][args.id2].remove(args.id1)
    save_links(links_data)
    print(f"✅ 已移除关联：{args.id1} ↔ {args.id2}\n")

def cmd_network(args):
    links_data = load_links()
    links = links_data.get('links', {})
    total_nodes = len(links)
    total_links = sum(len(v) for v in links.values()) // 2
    conn = defaultdict(int)
    for src, tgts in links.items():
        for t in tgts: conn[src] += 1
    
    print(f"\n🕸️  记忆网络统计")
    print(f"{'=' * 40}")
    print(f"有连接的节点：{total_nodes}")
    print(f"总连接数：{total_links}")
    if conn:
        top = sorted(conn.items(), key=lambda x: -x[1])[:5]
        print(f"\n🔗 最关联的记忆 TOP5:")
        for i, (nid, cnt) in enumerate(top, 1):
            print(f"  {i}. {nid}: {cnt} 条关联")
    print(f"{'=' * 40}\n")

def main():
    parser = argparse.ArgumentParser(description='炮哥大脑 v2.0 - 关联记忆模块')
    sub = parser.add_subparsers(dest='command')
    
    p_store = sub.add_parser('store', help='存入并自动关联')
    p_store.add_argument('text', help='记忆内容')
    p_store.add_argument('--emotion', choices=list(EMOTION_MAP.keys()), default='neutral')
    p_store.add_argument('--type', choices=list(TYPE_MAP.keys()), default='default')
    p_store.add_argument('--tags', default='')
    p_store.add_argument('--importance', type=int, default=5)
    p_store.add_argument('--auto-link', action='store_true', help='自动关联')
    
    p_links = sub.add_parser('links', help='查看关联')
    p_links.add_argument('--id', required=True)
    
    p_link = sub.add_parser('link', help='手动建立关联')
    p_link.add_argument('--id1', required=True)
    p_link.add_argument('--id2', required=True)
    
    p_unlink = sub.add_parser('unlink', help='移除关联')
    p_unlink.add_argument('--id1', required=True)
    p_unlink.add_argument('--id2', required=True)
    
    sub.add_parser('network', help='网络统计')
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    
    cmds = {'store': cmd_store, 'links': cmd_links, 'link': cmd_link, 'unlink': cmd_unlink, 'network': cmd_network}
    cmds[args.command](args)

if __name__ == '__main__':
    main()
