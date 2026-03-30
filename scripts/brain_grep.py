#!/usr/bin/env python3
"""
炮哥大脑 v2.2 - 关键词检索功能（类似 lossless-claw 的 lcm_grep）

用法：
  python brain_grep.py "螳螂拳"
  python brain_grep.py "情绪便利店" -n 10
  python brain_grep.py "火柴人" --tags
"""

import os
import sys
import json
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

BRAIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'brain-data')
DB_DIR = os.path.join(BRAIN_DIR, 'vectordb')
COLLECTION_NAME = "paoge_brain"


def get_collection():
    if not HAS_CHROMADB:
        print("错误：需要安装 chromadb。运行：pip install chromadb")
        sys.exit(1)
    
    os.makedirs(DB_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=DB_DIR)
    return client.get_or_create_collection(name=COLLECTION_NAME)


def cmd_grep(keyword, limit=10, tags_only=False):
    """关键词检索"""
    collection = get_collection()
    
    # 获取所有记忆
    all_data = collection.get(include=["documents", "metadatas"])
    
    if not all_data['ids']:
        print("🧠 炮哥大脑：还没有记忆")
        return
    
    # 关键词匹配
    matches = []
    keyword_lower = keyword.lower()
    
    for i, doc_id in enumerate(all_data['ids']):
        doc = all_data['documents'][i]
        meta_data = all_data['metadatas'][i]
        
        # 检查文档内容是否包含关键词
        if not tags_only and keyword_lower in doc.lower():
            matches.append({
                'id': doc_id,
                'document': doc,
                'metadata': meta_data,
                'score': 1.0,
                'match_type': '内容'
            })
        else:
            # 检查 tags 是否包含关键词
            tags = json.loads(meta_data.get('tags', '[]'))
            for tag in tags:
                if keyword_lower in tag.lower():
                    matches.append({
                        'id': doc_id,
                        'document': doc,
                        'metadata': meta_data,
                        'score': 0.8,
                        'match_type': '标签'
                    })
                    break
    
    if not matches:
        print(f"🔍 炮哥大脑：没有找到包含 \"{keyword}\" 的记忆")
        return
    
    # 按匹配度排序
    matches.sort(key=lambda x: x['score'], reverse=True)
    matches = matches[:limit]
    
    print(f"\n🧠 炮哥大脑 v2.2 - 关键词检索：\"{keyword}\"")
    print(f"找到 {len(matches)} 条匹配记忆（共 {len(all_data['ids'])} 条）")
    print(f"{'=' * 70}")
    
    for i, match in enumerate(matches, 1):
        meta_data = match['metadata']
        stored_at = meta_data.get('stored_at', '')[:10] if meta_data.get('stored_at') else 'unknown'
        importance = meta_data.get('importance', 5)
        tags = json.loads(meta_data.get('tags', '[]'))
        source = meta_data.get('source', 'unknown')
        
        print(f"\n[{i}] 📌 重要度：{importance}/10 | 📅 {stored_at} | 🏷️  {', '.join(tags) if tags else '无'}")
        print(f"    来源：{source} | 匹配：{match['match_type']}")
        print(f"    内容：{match['document'][:200]}{'...' if len(match['document']) > 200 else ''}")
        print(f"{'-' * 70}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='🧠 炮哥大脑 v2.2 - 关键词检索')
    parser.add_argument('keyword', help='搜索关键词')
    parser.add_argument('-n', type=int, default=10, help='返回条数（默认 10）')
    parser.add_argument('--tags', action='store_true', help='只搜索标签')
    
    args = parser.parse_args()
    
    cmd_grep(args.keyword, args.n, args.tags)


if __name__ == '__main__':
    main()
