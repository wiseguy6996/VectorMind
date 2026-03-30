#!/usr/bin/env python3
"""
炮哥大脑 v1.0 - 向量记忆系统
三层记忆架构：本能层(SOUL) + 工作层(STATUS) + 长期层(向量检索)

用法：
  python brain.py store "螳螂拳动作捕捉验证成功，与原视频一致"
  python brain.py store "骨盆骨骼层级多了一层hip导致身体被钉住" --tags "螳螂拳,骨骼,bug"
  python brain.py recall "螳螂拳骨骼问题"
  python brain.py recall "情绪便利店怎么收费"
  python brain.py forget --days 90 --threshold 0
  python brain.py stats
  python brain.py import-md memory/2026-03-25.md
"""

import os
import sys
import json
import argparse
import hashlib
from datetime import datetime, timedelta

# 修复 Windows 控制台编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

BRAIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'brain-data')
DB_DIR = os.path.join(BRAIN_DIR, 'vectordb')
META_FILE = os.path.join(BRAIN_DIR, 'brain-meta.json')

COLLECTION_NAME = "paoge_brain"


def ensure_dirs():
    os.makedirs(BRAIN_DIR, exist_ok=True)
    os.makedirs(DB_DIR, exist_ok=True)


def get_client():
    if not HAS_CHROMADB:
        print("错误：需要安装 chromadb。运行: pip install chromadb")
        sys.exit(1)
    ensure_dirs()
    client = chromadb.PersistentClient(path=DB_DIR)
    return client


def get_collection(client):
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "炮哥的大脑 - 长期向量记忆"}
    )


def load_meta():
    if os.path.exists(META_FILE):
        with open(META_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"version": "1.0", "total_stored": 0, "total_recalled": 0, "created": datetime.now().isoformat()}


def save_meta(meta):
    ensure_dirs()
    with open(META_FILE, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def gen_id(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:16]


def cmd_store(args):
    """存入记忆"""
    client = get_client()
    collection = get_collection(client)
    meta = load_meta()

    text = args.text
    tags = args.tags.split(',') if args.tags else []
    source = args.source or "manual"
    importance = args.importance or 5

    doc_id = gen_id(text + datetime.now().isoformat())

    metadata = {
        "source": source,
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

    print(f"✅ 记忆已存入！")
    print(f"   内容: {text[:80]}{'...' if len(text) > 80 else ''}")
    print(f"   标签: {tags}")
    print(f"   重要度: {importance}/10")
    print(f"   ID: {doc_id}")


def cmd_recall(args):
    """检索记忆"""
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
        print(f"未找到与 '{query}' 相关的记忆")
        return

    meta["total_recalled"] = meta.get("total_recalled", 0) + 1
    save_meta(meta)

    print(f"\n🧠 搜索: \"{query}\"")
    print(f"找到 {len(results['documents'][0])} 条相关记忆：\n")

    for i, (doc, meta_item, distance) in enumerate(zip(
        results['documents'][0],
        results['metadatas'][0],
        results['distances'][0]
    ), 1):
        tags = json.loads(meta_item.get('tags', '[]'))
        importance = meta_item.get('importance', 5)
        stored_at = meta_item.get('stored_at', 'unknown')
        relevance = max(0, round((1 - distance / 2) * 100, 1))

        print(f"[{i}] 相关度: {relevance}% | 重要度: {importance}/10")
        print(f"    {doc}")
        print(f"    标签: {tags} | 存入: {stored_at[:10]}")
        print()

        # 更新 recall_count
        doc_id = results['ids'][0][i-1]
        new_meta = dict(meta_item)
        new_meta['recall_count'] = int(new_meta.get('recall_count', 0)) + 1
        new_meta['last_recalled'] = datetime.now().isoformat()
        collection.update(ids=[doc_id], metadatas=[new_meta])


def cmd_forget(args):
    """遗忘：清理低重要度+长时间未使用的记忆"""
    client = get_client()
    collection = get_collection(client)

    days = args.days or 90
    threshold = args.threshold if args.threshold is not None else 0
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    # 获取所有记忆
    all_data = collection.get(include=["metadatas", "documents"])
    if not all_data['ids']:
        print("记忆库为空，无需清理")
        return

    to_delete = []
    for doc_id, meta_item, doc in zip(all_data['ids'], all_data['metadatas'], all_data['documents']):
        importance = int(meta_item.get('importance', 5))
        recall_count = int(meta_item.get('recall_count', 0))
        stored_at = meta_item.get('stored_at', '')

        # 低重要度 + 从未被检索 + 存入时间超过阈值
        if importance <= threshold and recall_count == 0 and stored_at < cutoff:
            to_delete.append((doc_id, doc[:50]))

    if not to_delete:
        print(f"没有需要遗忘的记忆（条件：重要度≤{threshold}，{days}天未被检索）")
        return

    if not args.force:
        print(f"即将遗忘 {len(to_delete)} 条记忆：")
        for doc_id, preview in to_delete[:10]:
            print(f"  - {preview}...")
        confirm = input(f"\n确认遗忘？(y/n): ")
        if confirm.lower() != 'y':
            print("取消")
            return

    collection.delete(ids=[d[0] for d in to_delete])
    print(f"✅ 已遗忘 {len(to_delete)} 条记忆")


def cmd_stats(args):
    """统计"""
    client = get_client()
    collection = get_collection(client)
    meta = load_meta()

    count = collection.count()

    print(f"\n🧠 炮哥大脑 v1.0 统计")
    print(f"{'=' * 40}")
    print(f"总记忆数: {count}")
    print(f"累计存入: {meta.get('total_stored', 0)}")
    print(f"累计检索: {meta.get('total_recalled', 0)}")
    print(f"创建时间: {meta.get('created', 'unknown')[:10]}")
    print(f"数据目录: {DB_DIR}")
    print(f"{'=' * 40}")

    if count > 0:
        all_data = collection.get(include=["metadatas"])
        importances = [int(m.get('importance', 5)) for m in all_data['metadatas']]
        recall_counts = [int(m.get('recall_count', 0)) for m in all_data['metadatas']]
        avg_importance = sum(importances) / len(importances)
        total_recalls = sum(recall_counts)
        never_recalled = sum(1 for r in recall_counts if r == 0)

        print(f"平均重要度: {avg_importance:.1f}/10")
        print(f"总被检索次数: {total_recalls}")
        print(f"从未被检索: {never_recalled} 条 ({never_recalled/count*100:.0f}%)")
        print(f"{'=' * 40}")


def cmd_import_md(args):
    """从 Markdown 文件导入记忆"""
    filepath = args.file
    if not os.path.exists(filepath):
        print(f"错误：文件不存在: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 按段落分割
    paragraphs = []
    current = []
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            if current:
                text = ' '.join(current)
                if len(text) > 20:  # 过滤太短的
                    paragraphs.append(text)
                current = []
        else:
            # 跳过标题行和分隔线
            if line.startswith('#') or line.startswith('---') or line.startswith('|'):
                if current:
                    text = ' '.join(current)
                    if len(text) > 20:
                        paragraphs.append(text)
                    current = []
                # 标题也存
                if line.startswith('#'):
                    clean = line.lstrip('#').strip()
                    if len(clean) > 5:
                        paragraphs.append(clean)
            else:
                current.append(line)

    if current:
        text = ' '.join(current)
        if len(text) > 20:
            paragraphs.append(text)

    if not paragraphs:
        print("没有找到可导入的内容")
        return

    client = get_client()
    collection = get_collection(client)
    meta = load_meta()

    filename = os.path.basename(filepath)
    imported = 0

    for para in paragraphs:
        doc_id = gen_id(para)

        # 检查是否已存在
        existing = collection.get(ids=[doc_id])
        if existing and existing['ids']:
            continue

        metadata = {
            "source": f"import:{filename}",
            "tags": json.dumps([filename.replace('.md', '')], ensure_ascii=False),
            "importance": 5,
            "recall_count": 0,
            "stored_at": datetime.now().isoformat(),
            "last_recalled": "",
        }

        collection.add(
            documents=[para],
            metadatas=[metadata],
            ids=[doc_id]
        )
        imported += 1

    meta["total_stored"] = meta.get("total_stored", 0) + imported
    save_meta(meta)

    print(f"✅ 从 {filename} 导入 {imported} 条记忆（跳过 {len(paragraphs) - imported} 条重复）")


def main():
    parser = argparse.ArgumentParser(description='炮哥大脑 v1.0 - 向量记忆系统')
    subparsers = parser.add_subparsers(dest='command', help='命令')

    # store
    p_store = subparsers.add_parser('store', help='存入记忆')
    p_store.add_argument('text', help='记忆内容')
    p_store.add_argument('--tags', default='', help='标签（逗号分隔）')
    p_store.add_argument('--source', default='manual', help='来源')
    p_store.add_argument('--importance', type=int, default=5, help='重要度 1-10')

    # recall
    p_recall = subparsers.add_parser('recall', help='检索记忆')
    p_recall.add_argument('query', help='搜索关键词')
    p_recall.add_argument('-n', type=int, default=5, help='返回条数')

    # forget
    p_forget = subparsers.add_parser('forget', help='遗忘低价值记忆')
    p_forget.add_argument('--days', type=int, default=90, help='超过多少天')
    p_forget.add_argument('--threshold', type=int, default=0, help='重要度阈值')
    p_forget.add_argument('--force', action='store_true', help='不确认直接删除')

    # stats
    subparsers.add_parser('stats', help='统计信息')

    # import-md
    p_import = subparsers.add_parser('import-md', help='从 Markdown 文件导入')
    p_import.add_argument('file', help='Markdown 文件路径')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        'store': cmd_store,
        'recall': cmd_recall,
        'forget': cmd_forget,
        'stats': cmd_stats,
        'import-md': cmd_import_md,
    }

    commands[args.command](args)


if __name__ == '__main__':
    main()
