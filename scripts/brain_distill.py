#!/usr/bin/env python3
"""
记忆大王 v2.0 - 记忆蒸馏
自动摘要生成、核心记忆提炼、周报/月报报告

功能：
1. 每日摘要 - 提炼当天核心记忆
2. 周报生成 - 7 天记忆自动总结
3. 月报生成 - 30 天记忆自动总结
4. 核心记忆提炼 - 重要度≥9 的记忆提取
"""

import os
import sys
import json
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

BRAIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'brain-data')
DB_DIR = os.path.join(BRAIN_DIR, 'vectordb')
DISTILL_DIR = os.path.join(BRAIN_DIR, 'distilled')

COLLECTION_NAME = "paoge_brain"


def ensure_dirs():
    os.makedirs(DISTILL_DIR, exist_ok=True)


def get_client():
    if not HAS_CHROMADB:
        print("错误：需要安装 chromadb。运行：pip install chromadb")
        sys.exit(1)
    ensure_dirs()
    client = chromadb.PersistentClient(path=DB_DIR)
    return client


def get_collection(client):
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "炮哥的大脑 - 长期向量记忆"}
    )


def parse_datetime(dt_str):
    """解析 ISO 格式日期字符串"""
    try:
        return datetime.fromisoformat(dt_str)
    except:
        return None


def extract_keywords(text, top_n=5):
    """
    从文本中提取关键词（简单版）
    实际应该用 NLP 模型，这里用简单规则
    """
    # 中文分词（简单版：按标点和空格分割）
    import re
    words = re.split(r'[，。！？、；：""''\s]+', text)
    
    # 过滤短词和停用词
    stopwords = {'的', '了', '是', '在', '和', '与', '及', '等', '个', '这', '那', '之', '就', '都', '而', '及', '与', '或'}
    words = [w for w in words if len(w) >= 2 and w not in stopwords]
    
    # 统计词频
    from collections import Counter
    word_counts = Counter(words)
    
    # 返回 top_n 个关键词
    return [word for word, count in word_counts.most_common(top_n)]


def cluster_memories(memories, n_clusters=5):
    """
    将记忆聚类为主题（简单版）
    实际应该用聚类算法，这里用标签分组
    """
    clusters = defaultdict(list)
    
    for memory in memories:
        tags = memory.get('tags', '[]')
        try:
            tag_list = json.loads(tags)
            if tag_list:
                # 用第一个标签作为类别
                cluster_key = tag_list[0]
            else:
                cluster_key = '其他'
        except:
            cluster_key = '其他'
        
        clusters[cluster_key].append(memory)
    
    return dict(clusters)


def generate_summary(memories, title="记忆蒸馏报告"):
    """生成记忆摘要报告"""
    if not memories:
        return "没有记忆需要蒸馏"
    
    # 按重要度排序
    memories.sort(key=lambda x: -x.get('importance', 5))
    
    # 聚类
    clusters = cluster_memories(memories)
    
    # 生成报告
    report = []
    report.append(f"# {title}")
    report.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append(f"**记忆总数**: {len(memories)} 条")
    report.append(f"**分类数量**: {len(clusters)} 个")
    report.append("\n---\n")
    
    # 核心记忆（重要度≥9）
    core_memories = [m for m in memories if m.get('importance', 5) >= 9]
    if core_memories:
        report.append("## 🎯 核心记忆\n")
        for i, m in enumerate(core_memories[:10], 1):
            report.append(f"{i}. {m['document']}")
            report.append(f"   - 重要度：{m.get('importance', 5)}/10 | 标签：{m.get('tags', '[]')}")
        report.append("")
    
    # 按分类展示
    report.append("## 📊 分类摘要\n")
    for category, items in clusters.items():
        report.append(f"### {category} ({len(items)}条)\n")
        for i, m in enumerate(items[:5], 1):
            report.append(f"{i}. {m['document'][:80]}...")
        if len(items) > 5:
            report.append(f"... 还有{len(items)-5}条")
        report.append("")
    
    # 关键词统计
    all_text = ' '.join([m['document'] for m in memories])
    keywords = extract_keywords(all_text, top_n=10)
    report.append("## 🔑 关键词\n")
    report.append(", ".join(keywords))
    report.append("")
    
    return "\n".join(report)


def cmd_daily(args):
    """生成每日摘要"""
    client = get_client()
    collection = get_collection(client)
    
    # 获取今天的记忆
    today = datetime.now().date()
    
    all_data = collection.get(include=["metadatas", "documents"])
    
    if not all_data['ids']:
        print("记忆库为空")
        return
    
    today_memories = []
    for doc_id, meta_item, doc in zip(all_data['ids'], all_data['metadatas'], all_data['documents']):
        stored_at = parse_datetime(meta_item.get('stored_at', ''))
        if stored_at and stored_at.date() == today:
            today_memories.append({
                'id': doc_id,
                'document': doc,
                'importance': int(meta_item.get('importance', 5)),
                'tags': meta_item.get('tags', '[]'),
                'stored_at': stored_at.strftime('%Y-%m-%d %H:%M')
            })
    
    if not today_memories:
        print(f"今天 ({today}) 还没有存入记忆")
        return
    
    # 生成摘要
    report = generate_summary(today_memories, f"每日记忆摘要 ({today})")
    
    # 保存到文件
    output_file = os.path.join(DISTILL_DIR, f"daily_{today}.md")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ 每日摘要已生成：{output_file}")
    print(f"📊 今日记忆：{len(today_memories)} 条")
    print(f"🎯 核心记忆：{len([m for m in today_memories if m['importance'] >= 9])} 条")


def cmd_weekly(args):
    """生成周报"""
    client = get_client()
    collection = get_collection(client)
    
    # 获取最近 7 天的记忆
    today = datetime.now().date()
    week_start = today - timedelta(days=7)
    
    all_data = collection.get(include=["metadatas", "documents"])
    
    if not all_data['ids']:
        print("记忆库为空")
        return
    
    week_memories = []
    for doc_id, meta_item, doc in zip(all_data['ids'], all_data['metadatas'], all_data['documents']):
        stored_at = parse_datetime(meta_item.get('stored_at', ''))
        if stored_at and week_start <= stored_at.date() <= today:
            week_memories.append({
                'id': doc_id,
                'document': doc,
                'importance': int(meta_item.get('importance', 5)),
                'tags': meta_item.get('tags', '[]'),
                'stored_at': stored_at.strftime('%Y-%m-%d')
            })
    
    if not week_memories:
        print(f"过去 7 天没有记忆")
        return
    
    # 生成周报
    report = generate_summary(week_memories, f"周报 ({week_start} ~ {today})")
    
    # 添加到周报
    report += "\n\n## 📈 本周统计\n"
    report += f"- 总记忆数：{len(week_memories)} 条\n"
    report += f"- 核心记忆：{len([m for m in week_memories if m['importance'] >= 9])} 条\n"
    report += f"- 平均重要度：{sum(m['importance'] for m in week_memories)/len(week_memories):.1f}/10\n"
    
    # 保存到文件
    output_file = os.path.join(DISTILL_DIR, f"weekly_{week_start}_to_{today}.md")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ 周报已生成：{output_file}")
    print(f"📊 本周记忆：{len(week_memories)} 条")
    print(f"🎯 核心记忆：{len([m for m in week_memories if m['importance'] >= 9])} 条")


def cmd_monthly(args):
    """生成月报"""
    client = get_client()
    collection = get_collection(client)
    
    # 获取最近 30 天的记忆
    today = datetime.now().date()
    month_start = today - timedelta(days=30)
    
    all_data = collection.get(include=["metadatas", "documents"])
    
    if not all_data['ids']:
        print("记忆库为空")
        return
    
    month_memories = []
    for doc_id, meta_item, doc in zip(all_data['ids'], all_data['metadatas'], all_data['documents']):
        stored_at = parse_datetime(meta_item.get('stored_at', ''))
        if stored_at and month_start <= stored_at.date() <= today:
            month_memories.append({
                'id': doc_id,
                'document': doc,
                'importance': int(meta_item.get('importance', 5)),
                'tags': meta_item.get('tags', '[]'),
                'stored_at': stored_at.strftime('%Y-%m-%d')
            })
    
    if not month_memories:
        print(f"过去 30 天没有记忆")
        return
    
    # 生成月报
    report = generate_summary(month_memories, f"月报 ({month_start} ~ {today})")
    
    # 添加到月报
    report += "\n\n## 📈 本月统计\n"
    report += f"- 总记忆数：{len(month_memories)} 条\n"
    report += f"- 核心记忆：{len([m for m in month_memories if m['importance'] >= 9])} 条\n"
    report += f"- 平均重要度：{sum(m['importance'] for m in month_memories)/len(month_memories):.1f}/10\n"
    
    # 按日期分组统计
    date_groups = defaultdict(int)
    for m in month_memories:
        date_groups[m['stored_at']] += 1
    
    report += "\n## 📅 每日记忆分布\n"
    for date in sorted(date_groups.keys()):
        count = date_groups[date]
        bar = "█" * min(count, 20)  # 可视化条
        report += f"- {date}: {count}条 {bar}\n"
    
    # 保存到文件
    output_file = os.path.join(DISTILL_DIR, f"monthly_{month_start}_to_{today}.md")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ 月报已生成：{output_file}")
    print(f"📊 本月记忆：{len(month_memories)} 条")
    print(f"🎯 核心记忆：{len([m for m in month_memories if m['importance'] >= 9])} 条")


def cmd_core(args):
    """提炼核心记忆（重要度≥9）"""
    client = get_client()
    collection = get_collection(client)
    
    all_data = collection.get(include=["metadatas", "documents"])
    
    if not all_data['ids']:
        print("记忆库为空")
        return
    
    core_memories = []
    for doc_id, meta_item, doc in zip(all_data['ids'], all_data['metadatas'], all_data['documents']):
        importance = int(meta_item.get('importance', 5))
        if importance >= 9:
            core_memories.append({
                'id': doc_id,
                'document': doc,
                'importance': importance,
                'tags': meta_item.get('tags', '[]'),
                'stored_at': meta_item.get('stored_at', 'unknown')
            })
    
    if not core_memories:
        print("没有核心记忆（重要度≥9）")
        return
    
    # 按重要度排序
    core_memories.sort(key=lambda x: -x['importance'])
    
    # 生成核心记忆列表
    report = []
    report.append("# 核心记忆清单")
    report.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append(f"**核心记忆数**: {len(core_memories)} 条")
    report.append(f"**筛选标准**: 重要度 ≥ 9/10")
    report.append("\n---\n")
    
    for i, m in enumerate(core_memories, 1):
        report.append(f"## {i}. 重要度：{m['importance']}/10")
        report.append(f"**存入时间**: {m['stored_at']}")
        report.append(f"**标签**: {m['tags']}")
        report.append(f"\n{m['document']}\n")
        report.append("---\n")
    
    # 保存到文件
    output_file = os.path.join(DISTILL_DIR, f"core_memories_{datetime.now().strftime('%Y%m%d')}.md")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
    
    print(f"✅ 核心记忆已提炼：{output_file}")
    print(f"🎯 核心记忆数：{len(core_memories)} 条")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='记忆大王 v2.0 - 记忆蒸馏')
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # daily - 每日摘要
    subparsers.add_parser('daily', help='生成每日摘要')
    
    # weekly - 周报
    subparsers.add_parser('weekly', help='生成周报')
    
    # monthly - 月报
    subparsers.add_parser('monthly', help='生成月报')
    
    # core - 核心记忆提炼
    subparsers.add_parser('core', help='提炼核心记忆（重要度≥9）')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    ensure_dirs()
    
    if args.command == 'daily':
        cmd_daily(args)
    elif args.command == 'weekly':
        cmd_weekly(args)
    elif args.command == 'monthly':
        cmd_monthly(args)
    elif args.command == 'core':
        cmd_core(args)


if __name__ == '__main__':
    main()
