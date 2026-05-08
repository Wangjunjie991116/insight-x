---
name: chinese-code-comments
description: Guides adding concise 简体中文 comments at workflow boundaries and on core functions for readability. Use when implementing or refactoring Python/TS code, agents, orchestrators, APIs, or when the user asks for readable/commented code in Chinese.
---

# 中文注释（流程与核心函数）

## 何时加载本技能

用户希望代码易读、要求在**业务流程**与**核心函数**上补充中文说明时；或编辑 Agent 编排、入口 API、复杂分支时主动采用。

## 执行要点

1. **语言**：行间注释与文档字符串使用**简体中文**；符号名、类型、第三方 API 保持英文。
2. **流程**：对多阶段流水线（例如 Agent 串联、异步任务阶段、`try/finally` 资源边界），在阶段开头用 1～3 句说明「本步做什么、与上下步关系」。无需逐步复述显而易见的赋值。
3. **核心函数**：对模块对外入口、`execute`/`run`、路由 handler、共享工具中的「非一眼能懂」函数：
   - 用简短文档字符串说明：职责、关键参数含义、返回值、可能抛错或失败语义。
   - 复杂不变量或安全假设（如「仅允许 SELECT」）写在紧邻逻辑处。
4. **克制**：不注释「导入 os」这类代码自解释内容；不中英混写同一句（专有名词除外）。

## 自检清单

- [ ] 编排或状态迁移的路径上有阶段级中文说明。
- [ ] 对外与核心私有函数有文档字符串或等价模块注释。
- [ ] 无冗余复述代码的注释。
