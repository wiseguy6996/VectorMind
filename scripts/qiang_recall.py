#!/usr/bin/env python3
"""
小强专属记忆检索脚本 - 简化版
用法：python qiang_recall.py <关键词>
"""

import subprocess
import sys

def main():
    if len(sys.argv) < 2:
        print("用法：python qiang_recall.py <关键词>")
        print("示例：python qiang_recall.py CLI-Anything")
        return
    
    query = " ".join(sys.argv[1:])
    
    # 常用检索预设
    presets = {
        "cli": "CLI-Anything Blender",
        "blender": "Blender CLI 实测",
        "螳螂拳": "螳螂拳 CLI 1132 帧",
        "骨骼": "螳螂拳 骨骼 hip 骨盆",
        "小强": "小强 CLI-Anything 验证",
    }
    
    # 匹配预设
    for key, preset_query in presets.items():
        if key in query:
            query = preset_query
            break
    
    # 调用 brain.py
    cmd = [
        sys.executable,
        "brain.py",
        "recall",
        query,
        "-n", "10"
    ]
    
    subprocess.run(cmd, cwd=sys.path[0])

if __name__ == "__main__":
    main()
