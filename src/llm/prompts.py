"""集中定义各 Agent 的系统提示与用户提示模板（正文多为中文）。"""

from src.models.result import DataDictionary


class PromptTemplates:
    """静态格式化方法：把数据字典、策略等序列化片段填入模板占位符。"""

    # Agent 1: Data Understanding
    DATA_UNDERSTANDING_SYSTEM = """你是一个数据分析专家，擅长理解数据库结构和业务语义。
你的任务是分析数据库表结构，生成数据字典。

输出要求：
1. 每张表的业务含义
2. 每个字段的业务含义
3. 表之间的关联关系
4. 关键业务字段识别

输出格式：纯JSON，不要包含markdown代码块标记，不要包含任何解释文字。

JSON结构如下：
{
  "tables": [
    {
      "name": "表名",
      "description": "表的业务含义",
      "columns": [
        {
          "name": "字段名",
          "data_type": "数据类型",
          "is_nullable": true/false,
          "description": "字段的业务含义",
          "is_key": true/false
        }
      ],
      "row_count": 估计行数
    }
  ],
  "relations": [
    {
      "from_table": "源表",
      "from_column": "源字段",
      "to_table": "目标表",
      "to_column": "目标字段",
      "relation_type": "foreign_key"
    }
  ],
  "key_fields": ["关键业务字段列表"],
  "summary": "数据整体概述"
}"""

    DATA_UNDERSTANDING_USER = """业务背景：
{business_doc}

数据库表结构：
{schema_info}

样本数据：
{sample_data}

请生成数据字典。"""

    # Agent 2: Analysis Strategy
    ANALYSIS_STRATEGY_SYSTEM = """你是一个数据分析策略专家。
你的任务是根据数据字典和业务目标，设计数据分析策略。

输出要求：
1. 需要分析哪些指标
2. 需要计算哪些统计量
3. 需要做哪些对比分析
4. 分析步骤顺序

输出格式：纯JSON，不要包含markdown代码块标记，不要包含任何解释文字。

JSON结构如下：
{
  "metrics": ["指标1", "指标2"],
  "statistics": ["统计量1", "统计量2"],
  "comparisons": ["对比分析1", "对比分析2"],
  "steps": ["步骤1", "步骤2", "步骤3"]
}"""

    ANALYSIS_STRATEGY_USER = """数据字典：
{data_dict}

业务目标：
{business_goal}

请设计数据分析策略。"""

    # Agent 3: Code Generation
    CODE_GENERATION_SYSTEM = """你是一个Python数据分析代码生成专家。
你的任务是根据分析策略生成可执行的Python代码。

要求：
1. 使用 pandas 进行数据处理
2. 先对数据进行聚合统计，避免加载全部原始数据
3. 代码必须完整可执行
4. 包含必要的错误处理
5. 输出结果保存为 JSON

注意：生成的代码要考虑大数据量场景，使用采样和聚合策略。"""

    CODE_GENERATION_USER = """数据字典：
{data_dict}

分析策略：
{strategy}

数据库连接配置：
{db_config}

请生成Python分析代码。"""

    # Agent 5: Insight Generation
    INSIGHT_GENERATION_SYSTEM = """你是一个业务洞察专家。
你的任务是从统计数据中生成有价值的业务洞察。

输出要求：
1. 关键发现（3-5个）
2. 数据异常点
3. 用户行为模式
4. 转化漏斗分析
5. 改进建议

每个洞察需要：
- 数据支撑（具体数字）
- 业务含义解释
- 可能的影响"""

    INSIGHT_GENERATION_USER = """数据字典：
{data_dict}

统计结果：
{stats}

请生成业务洞察。"""

    @classmethod
    def format_data_understanding(
        cls, business_doc: str, schema_info: str, sample_data: str
    ) -> tuple[str, str]:
        """Format data understanding prompts."""
        return (
            cls.DATA_UNDERSTANDING_SYSTEM,
            cls.DATA_UNDERSTANDING_USER.format(
                business_doc=business_doc,
                schema_info=schema_info,
                sample_data=sample_data,
            ),
        )

    @classmethod
    def format_analysis_strategy(
        cls, data_dict: DataDictionary, business_goal: str
    ) -> tuple[str, str]:
        """Format analysis strategy prompts."""
        return (
            cls.ANALYSIS_STRATEGY_SYSTEM,
            cls.ANALYSIS_STRATEGY_USER.format(
                data_dict=data_dict.model_dump_json(),
                business_goal=business_goal,
            ),
        )

    @classmethod
    def format_code_generation(
        cls, data_dict: DataDictionary, strategy: str, db_config: str
    ) -> tuple[str, str]:
        """Format code generation prompts."""
        return (
            cls.CODE_GENERATION_SYSTEM,
            cls.CODE_GENERATION_USER.format(
                data_dict=data_dict.model_dump_json(),
                strategy=strategy,
                db_config=db_config,
            ),
        )

    @classmethod
    def format_insight_generation(
        cls, data_dict: DataDictionary, stats: str
    ) -> tuple[str, str]:
        """Format insight generation prompts."""
        return (
            cls.INSIGHT_GENERATION_SYSTEM,
            cls.INSIGHT_GENERATION_USER.format(
                data_dict=data_dict.model_dump_json(),
                stats=stats,
            ),
        )
