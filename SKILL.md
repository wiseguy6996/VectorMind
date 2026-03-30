---
name: brain
description: 炮哥大脑 v2.2 - 向量记忆系统（含自动检索）。使用 ChromaDB 实现语义搜索，解决 AI 助手跨会话失忆问题。支持自动检索、记忆存入、检索、遗忘、统计和 Markdown 导入。
---

# 炮哥大脑 v2.2 - 向量记忆系统

## 概述

基于 ChromaDB 的向量记忆系统，实现 AI 助手的长期记忆能力。

**v2.2 新增：会话开始自动检索！**
- 🚀 **自动检索**：每次会话开始自动运行，防止忘记关键信息（如小强是 AI）
- 🧠 **语义搜索**：不用记关键词，一句话就能找到记忆
- 📦 **持久存储**：记忆存入向量数据库，不依赖 AI 短期记忆
- 🔍 **智能检索**：按相关度排序，自动推送最相关记忆
- 🗑️ **自动遗忘**：清理低价值记忆，保持大脑清爽

**核心价值：防止跨会话失忆！**
> 炮哥教训（2026-03-27）：炮哥开发了记忆大王，自己没用，结果忘记了小强是 AI！
> 现在每次会话开始自动检索，再也不会忘记了！

---

## 快速上手

### 存入记忆
```bash
python skills/brain/scripts/brain.py store "螳螂拳动作捕捉验证成功，与原视频一致" --tags "螳螂拳，验证" --importance 9
```

### 检索记忆
```bash
python skills/brain/scripts/brain.py recall "螳螂拳骨骼问题"
```

### 查看统计
```bash
python skills/brain/scripts/brain.py stats
```

### 导入 Markdown
```bash
python skills/brain/scripts/brain.py import-md MEMORY.md
```

---

## 命令详解

### store - 存入记忆

**用法**：
```bash
python brain.py store <记忆内容> [--tags <标签>] [--importance <1-10>]
```

**参数**：
- `text`: 记忆内容（必填）
- `--tags`: 标签，逗号分隔（可选）
- `--importance`: 重要度 1-10，默认 5（可选）
- `--source`: 来源，默认 manual（可选）

**示例**：
```bash
# 简单存入
python brain.py store "情绪便利店文案库 500 条已完成"

# 带标签和重要度
python brain.py store "CLI-Anything 实测成功，Blender 渲染 30 帧动画" --tags "CLI-Anything,Blender,验证" --importance 9

# 记录用户偏好
python brain.py store "视频比例 16:9 横屏，B 站用" --tags "偏好，视频" --importance 8
```

---

### recall - 检索记忆

**用法**：
```bash
python brain.py recall <搜索关键词> [-n <返回条数>]
```

**参数**：
- `query`: 搜索关键词（必填）
- `-n`: 返回条数，默认 5（可选）

**示例**：
```bash
# 搜索情绪便利店
python brain.py recall "情绪便利店怎么收费"

# 搜索螳螂拳相关
python brain.py recall "螳螂拳动作捕捉"

# 返回 10 条结果
python brain.py recall "Blender" -n 10
```

**输出格式**：
```
🧠 搜索："情绪便利店"
找到 5 条相关记忆：

[1] 相关度：100.0% | 重要度：9/10
    情绪便利店 5 个技能：夸夸/毒鸡汤/嘴替/动物语/运势
    标签：['情绪便利店', 'Skill'] | 存入：2026-03-26
```

---

### forget - 遗忘记忆

**用法**：
```bash
python brain.py forget [--days <天数>] [--threshold <重要度阈值>] [--force]
```

**参数**：
- `--days`: 超过多少天，默认 90（可选）
- `--threshold`: 重要度阈值，默认 0（可选）
- `--force`: 不确认直接删除（可选）

**示例**：
```bash
# 预览要遗忘的记忆
python brain.py forget --days 90 --threshold 0

# 直接删除（不确认）
python brain.py forget --days 90 --threshold 0 --force
```

**遗忘规则**：
- 重要度 ≤ threshold
- 从未被检索过（recall_count = 0）
- 存入时间超过 days 天

---

### stats - 统计信息

**用法**：
```bash
python brain.py stats
```

**输出示例**：
```
🧠 炮哥大脑 v1.0 统计
========================================
总记忆数：127
累计存入：150
累计检索：45
创建时间：2026-03-25
数据目录：C:\...\brain-data\vectordb
========================================
平均重要度：7.2/10
总被检索次数：89
从未被检索：23 条 (18%)
========================================
```

---

### import-md - 导入 Markdown 文件

**用法**：
```bash
python brain.py import-md <Markdown 文件路径>
```

**示例**：
```bash
# 导入 MEMORY.md
python brain.py import-md MEMORY.md

# 导入每日记忆
python brain.py import-md memory/2026-03-25.md
```

**导入逻辑**：
- 按段落分割 Markdown 内容
- 跳过太短的段落（<20 字符）
- 自动去重（基于内容 MD5）
- 标签设置为文件名

---

## 三层记忆架构

### 1️⃣ 本能层（SOUL.md）
- **位置**：`SOUL.md`
- **内容**：AI 助手的核心人格和价值观
- **特点**：几乎不变，定义"我是谁"

### 2️⃣ 工作层（STATUS + 短期记忆）
- **位置**：`memory/YYYY-MM-DD.md`
- **内容**：每日会话记录、临时决策
- **特点**：频繁更新，定义"今天在做什么"

### 3️⃣ 长期层（向量记忆）
- **位置**：`brain-data/vectordb/`
- **内容**：重要决策、用户偏好、项目进度、教训
- **特点**：语义检索，定义"长期积累的智慧"

---

## 记忆写入规则

### ✅ 应该记录
- 用户明确说"记住这个"
- 用户偏好（视频比例、风格偏好、平台选择）
- 重要决策（工具选择、流程确定、战略调整）
- 项目里程碑（开始、完成、重大进展）
- 学到的教训（踩过的坑、成功经验）
- 技术验证结果（CLI-Anything 实测成功等）
- 新发现的资源（网站、工具、素材来源）

### ❌ 不应该记录
- 临时性信息（明天就过期的）
- 过于细节的操作步骤（除非是重要教训）
- 个人隐私/敏感信息（除非用户明确要求）
- 重复信息（已有记录的）

---

## 最佳实践

### 1. 会话开始自动检索
```python
# 读取用户问题
query = "情绪便利店"

# 自动检索相关记忆
python brain.py recall "情绪便利店"

# 把检索结果作为上下文给 AI
```

### 2. 会话结束自动存入
```python
# 识别重要信息
important_facts = [
    "情绪便利店本周上线 Vercel",
    "CLI-Anything 实测成功"
]

# 批量存入
for fact in important_facts:
    python brain.py store fact --importance 8
```

### 3. 定期整理（每周）
```bash
# 查看统计
python brain.py stats

# 清理低价值记忆
python brain.py forget --days 90 --threshold 0

# 导入新的 MEMORY.md
python brain.py import-md MEMORY.md
```

---

## 与其他技能协作

### + project-memory-manager
- `project-memory-manager`: 文件化管理项目记忆
- `brain`: 向量检索快速查找
- **协作方式**：项目进度写入文件，同时关键决策存入向量库

### + family-memory
- `family-memory`: 记录三人团情感时刻
- `brain`: 语义检索历史对话
- **协作方式**：重要对话同时存入两个系统

### + workflow-optimizer
- `workflow-optimizer`: 自动化工作流
- `brain`: 提供记忆检索能力
- **协作方式**：定时任务自动检索相关记忆

---

## 技术细节

### 依赖
```bash
pip install chromadb
```

### 数据结构
```python
{
    "id": "md5(text)[:16]",
    "document": "记忆内容文本",
    "metadata": {
        "source": "manual|import:filename|skill-name",
        "tags": ["标签 1", "标签 2"],
        "importance": 5,  # 1-10
        "recall_count": 0,
        "stored_at": "2026-03-26T07:30:00",
        "last_recalled": "2026-03-26T08:00:00"
    }
}
```

### 向量模型
- 默认使用 ChromaDB 内置模型
- 支持中文语义理解
- 无需额外配置

---

## 故障排除

**Q: 提示 chromadb 未安装**
```bash
pip install chromadb
```

**Q: 检索结果为空**
- 检查记忆库是否有内容：`python brain.py stats`
- 尝试更宽泛的关键词

**Q: 导入 Markdown 失败**
- 检查文件路径是否正确
- 确保文件是 UTF-8 编码

**Q: 记忆太多检索慢**
- 使用 `forget` 命令清理低价值记忆
- 减少 `-n` 参数返回条数

---

## 更新日志

| 日期 | 版本 | 更新内容 |
|------|------|---------|
| 2026-03-25 | v1.0 | 炮哥大脑 v1.0 发布，ChromaDB 向量记忆 |
| 2026-03-26 | v1.0 | 添加 SKILL.md，集成到 OpenClaw 技能库 |

---

**技能维护者**：炮哥（小开）  
**最后更新**：2026-03-26  
**版本**：v1.0  
**状态**：✅ 生产级验证通过
