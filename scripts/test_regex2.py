#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

msg = "5 分钟后汇报"

patterns = [
    r'(\d+) 分钟后 (汇报 | 提醒)',
    r'(\d+) 分钟后汇报',
    r'(\d+) 分钟.*汇报',
    r'\d+ 分钟',
]

print(f"测试消息：{msg}\n")

for i, p in enumerate(patterns, 1):
    match = re.search(p, msg)
    if match:
        print(f"Pattern {i} 匹配成功：{p}")
        print(f"  Groups: {match.groups()}")
    else:
        print(f"Pattern {i} 匹配失败：{p}")
