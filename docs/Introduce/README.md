# Introduce — 图示源文件

本目录存放 **Mermaid** 与 **PlantUML** 源码，与仓库说明文档中的架构描述一致，便于用编辑器插件或在线工具渲染、导出 PNG/SVG。

## 文件索引

| 主题                                                         | PlantUML |
| ------------------------------------------------------------ | -------- |
| 逻辑架构（API / 编排 / Agent / 基础设施 / 外部系统）         | [architecture.puml](architecture.puml) |
| 典型时序（任务创建 + 数据分析五步 + 代码优化扩展）           | [sequence-analysis-run.puml](sequence-analysis-run.puml) |
| 编排器流水线（Agent 1-5 主线 + Agent 6-1/6-2/7 扩展分支）    | [orchestrator-pipeline.puml](orchestrator-pipeline.puml) |

## 图示覆盖的 Agent

| Agent | 位置 | 对应流水线 |
|-------|------|-----------|
| Agent 1 数据理解 | AnalysisOrchestrator | 数据分析主线 |
| Agent 2 分析策略 | AnalysisOrchestrator | 数据分析主线 |
| Agent 3 代码生成 | AnalysisOrchestrator | 数据分析主线 |
| Agent 4 代码执行 | AnalysisOrchestrator | 数据分析主线 |
| Agent 5 洞察生成 | AnalysisOrchestrator | 数据分析主线 |
| Agent 6-1 代码优化分析 | CodeOptimizationOrchestrator | 代码优化扩展 |
| Agent 6-2 埋点策略建议 | CodeOptimizationOrchestrator | 代码优化扩展 |
| Agent 7 代码修改实现 | CodeOptimizationOrchestrator | 代码优化扩展 |

## 如何预览

- **PlantUML**：本地需 PlantUML + Graphviz（或使用 JetBrains / VS Code PlantUML 插件）；或使用公司内部渲染服务。

## 与 Markdown 汇总文档的关系

嵌入了同款图示的文字说明见上一级：[community-diagrams.md](../community-diagrams.md)。修改图示时建议 **先改本目录源文件**，再同步 Markdown 中的代码块（若仍需内嵌预览）。
