import re

msg = "5 分钟后汇报"
pattern = r"(\d+) 分钟后 (汇报 | 提醒)"

print(f"Message: {msg}")
print(f"Pattern: {pattern}")
print(f"Match: {re.search(pattern, msg)}")

# 尝试简单模式
pattern2 = r"(\d+) 分钟"
print(f"Pattern2: {pattern2}")
print(f"Match2: {re.search(pattern2, msg)}")

# 尝试更简单
pattern3 = r"分钟"
print(f"Pattern3: {pattern3}")
print(f"Match3: {re.search(pattern3, msg)}")
