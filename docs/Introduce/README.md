# Introduce — 图示源文件

本目录存放 **Mermaid** 与 **PlantUML** 源码，与仓库说明文档中的架构描述一致，便于用编辑器插件或在线工具渲染、导出 PNG/SVG。

## 文件索引

| 主题                                   | Mermaid                                                  | PlantUML |
| -------------------------------------- | -------------------------------------------------------- | -------- |
| 逻辑架构（组件与外部边界）             | [architecture.puml](architecture.puml)                   |
| 典型时序（创建任务 + 运行分析）        | [sequence-analysis-run.puml](sequence-analysis-run.puml) |
| 编排器五步与「执行失败仍生成洞察」分支 | [orchestrator-pipeline.puml](orchestrator-pipeline.puml) |

## 如何预览

- **PlantUML**：本地需 PlantUML + Graphviz（或使用 JetBrains / VS Code PlantUML 插件）；或使用公司内部渲染服务。

## 与 Markdown 汇总文档的关系

嵌入了同款图示的文字说明见上一级：[community-diagrams.md](../community-diagrams.md)。修改图示时建议 **先改本目录源文件**，再同步 Markdown 中的代码块（若仍需内嵌预览）。
