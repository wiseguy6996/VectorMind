#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
炮哥大脑 - 自动导出今日相关记忆

每天自动运行，检索最近的记忆并导出到 memory/brain-recall-today.md
供每次会话开始时自动读取

用法:
    python brain_auto_export.py
"""

import os
import sys

# 修复 Windows 控制台编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import subprocess
import json
from datetime import datetime

# 脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# brain/scripts -> brain -> skills -> workspace (3 层向上)
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))
MEMORY_DIR = os.path.join(WORKSPACE_DIR, "memory")
OUTPUT_FILE = os.path.join(MEMORY_DIR, "brain-recall-today.md")
BRAIN_PY = os.path.join(SCRIPT_DIR, "brain.py")

# 确保 memory 目录存在
os.makedirs(MEMORY_DIR, exist_ok=True)


def get_recall_queries():
    """
    返回今日需要检索的关键词列表
    这些关键词覆盖了当前活跃的项目和话题
    """
    return [
        "情绪便利店",
        "主角梦工厂",
        "三人团",
        "小强",
        "wiseguy",
        "Blender",
        "技能",
        "项目进度",
        "待办",
        "优先级",
    ]


def run_brain_command(args):
    """
    运行 brain.py 命令，返回输出
    """
    cmd = [sys.executable, BRAIN_PY] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "命令执行超时", 1
    except Exception as e:
        return "", str(e), 1


def parse_recall_output(output):
    """
    解析 recall 命令的输出，提取记忆条目
    """
    memories = []
    lines = output.split('\n')
    
    current_memory = None
    
    for line in lines:
        line = line.strip()
        
        # 匹配记忆条目：[1] 相关度：100.0% | 重要度：9/10
        if line.startswith('[') and '相关度' in line:
            if current_memory:
                memories.append(current_memory)
            current_memory = {"header": line, "content": ""}
        elif current_memory:
            # 记忆内容行
            if line.startswith('标签：') or line.startswith('存入：'):
                current_memory["metadata"] = line
            elif line and not line.startswith('🧠') and not line.startswith('找到'):
                current_memory["content"] += line + "\n"
    
    if current_memory:
        memories.append(current_memory)
    
    return memories


def main():
    print(f"🧠 炮哥大脑 - 自动导出今日相关记忆")
    print(f"=" * 50)
    
    # 先获取统计信息
    print(f"📊 获取记忆库统计...")
    stdout, stderr, code = run_brain_command(["stats"])
    
    total_memories = 0
    if "总记忆数" in stdout:
        for line in stdout.split('\n'):
            if "总记忆数" in line:
                try:
                    total_memories = int(line.split('：')[1].strip())
                except:
                    pass
    
    print(f"   记忆库总量：{total_memories} 条")
    print("")
    
    # 检索并导出
    all_sections = []
    
    for query in get_recall_queries():
        print(f"🔍 检索：{query}")
        stdout, stderr, code = run_brain_command(["recall", query, "-n", "3"])
        
        memories = parse_recall_output(stdout)
        
        if memories:
            section_lines = [f"### 🔍 \"{query}\"", ""]
            for mem in memories[:3]:
                content = mem.get("content", "").strip()
                header = mem.get("header", "")
                metadata = mem.get("metadata", "")
                
                if content:
                    section_lines.append(f"**{header}**")
                    section_lines.append(f"{content}")
                    if metadata:
                        section_lines.append(f"   _{metadata}_")
                    section_lines.append("")
            
            if len(section_lines) > 2:
                all_sections.append("\n".join(section_lines))
                print(f"   ✅ 找到 {len(memories)} 条相关记忆")
        else:
            print(f"   ⚪ 无相关记忆")
    
    # 生成输出文件
    today = datetime.now().strftime("%Y-%m-%d")
    
    if all_sections:
        content = f"""# 🧠 炮哥大脑 - 今日相关记忆

**自动生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**检索关键词**: {len(get_recall_queries())} 个  
**记忆库总量**: {total_memories} 条

---

> 💡 **使用说明**: 每次会话开始时自动读取此文件，获取炮哥大脑检索到的相关记忆。
> 这有助于保持跨会话的记忆连续性。

---

{chr(10).join(all_sections)}

---

**—— 炮哥大脑 v1.0 自动导出 🦞**
"""
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        
        print("")
        print(f"✅ 导出完成：{OUTPUT_FILE}")
        print(f"   共 {len(all_sections)} 个检索主题有相关记忆")
    else:
        # 即使没有结果，也创建一个空文件标记今天已运行
        content = f"""# 🧠 炮哥大脑 - 今日相关记忆

**自动生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**状态**: ⚪ 今日无相关记忆（记忆库可能为空）

---

> 💡 炮哥大脑还没有存入足够的记忆。开始使用 `brain.py store` 存入记忆吧！

**—— 炮哥大脑 v1.0 自动导出 🦞**
"""
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        
        print("")
        print(f"⚠️ 记忆库为空，已创建空标记文件：{OUTPUT_FILE}")
    
    print("")
    print(f"🦞 炮哥大脑自动化完成！")


if __name__ == "__main__":
    main()
