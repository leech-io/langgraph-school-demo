# LangGraph 学生成绩查询 Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 当前会话直接执行。

**Goal:** 交付独立于Dify、实时查询student_grades的LangGraph浏览器Demo。
**Architecture:** StateGraph控制生成、校验、执行、有限纠正和汇总；LangChain适配模型；Streamlit提供交互与轨迹展示。
**Tech Stack:** Python3.12、uv、LangGraph、LangChain、SQLAlchemy、PyMySQL、Pydantic、sqlglot、Streamlit、Plotly、pytest。
**Spec:** ../specs/2026-11-26-school-query-design.md

## Global Constraints
只读student_grades，不修改用户数据或权限；最多10条查询、200行展示、5秒查询/连接超时、最多修正2次；本地127.0.0.1:8502；秘密仅本地配置；无自动提交/推送/部署。

## Review Focus
危险SELECT/CTE绕过(Task1)；异常泄露连接信息(Task1)；并列排名和去重口径(Task2/4)；重试越界及不完整结果(Task2)；图表与原始数据不一致(Task3)。

### Task1：配置、数据库与SQL边界
Files: pyproject.toml、uv.lock、.env.example、.gitignore；src/school_agent/config.py、db.py、sql_guard.py；tests/test_config.py、test_db.py、test_sql_guard.py。
Interfaces: Settings；inspect_schema(settings)->SchemaInfo；validate_sql(sql,schema)->ValidatedQuery；execute_readonly(query,settings)->QueryResult(columns,rows,truncated)。
- [x] 确认批准范围，读取目录约定，检查Git与隔离环境；无仓库则初始化，在feature分支实现。
- [x] 先写失败测试：安全SELECT/CTE通过；跨库、写操作、多语句、锁/文件/危险函数拒绝；截断/超时和秘密脱敏正确。
- [x] 跑pytest对应测试确认失败，然后创建依赖/虚拟环境并实现接口、AST白名单、只读事务及限制。
- [x] 只读核验MySQL版本、schema和账号授权；本地读取配置，不打印URI/Key。缺项要求用户在本地补齐，普通单元工作继续。
- [x] 跑对应测试至通过。

### Task2：LangGraph执行与纠正
Files: src/school_agent/state.py、model.py、prompts.py、graph.py；tests/test_graph.py、test_business_rules.py。
Interfaces: build_graph(settings,db,model)->CompiledStateGraph；输入question，输出queries/results/errors/answer/trace；复用Task1模型。
- [x] 先写失败测试：成功、无数据、坏JSON、SQL纠正成功、2次上限停止、危险查询不执行、连接错误不纠正、部分失败披露。
- [x] 独立夹具覆盖并列、未ROUND排序、去重人数和学期口径；运行测试确认预期失败。
- [x] 实现节点/条件边和结构化计划，复用Dify业务提示，移除插件专属输出格式；trace脱敏。
- [x] 跑对应测试至通过，并验证实际模型接口可用，记录真实失败原因。

### Task3：交互界面和图表
Files: app.py、src/school_agent/charts.py；tests/test_charts.py、test_app.py。
Interfaces: render_chart(result,chart_spec)->PlotlyFigure；spec只能引用QueryResult字段。界面调用Task2图。
- [x] 先写图表/界面失败测试：标签数值一致，无数据/非数值/负数饼图降级，历史不会代替新查询。
- [x] 跑测试确认失败，实现中文提问、答案、SQL、表格、图表、trace和清空会话；显示超时、截断、部分失败。
- [x] 跑测试至通过；启动 python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502。
- [x] 浏览器核验提问、表格、三类图表和错误提示，确认原Dify可访问。

### Task4：真实验收和交付
Files: scripts/acceptance.py、tests/acceptance_cases.json、README.md、docs/acceptance-report.md。
Interfaces: 验收用graph处理自然语言问题，用独立人工SQL读取同库作为基准，标准化Decimal/日期/排序后比较。
- [x] 依据真实班级/科目/学期构造设计规定至少8项案例，禁止向用户库插入夹具。
- [x] 跑全套pytest和真实模型验收；写明通过/失败、SQL、基准与实际结果，不能用模型自评替代基准。
- [x] README写明启动、.env、模型数据流、架构和限制。
- [x] 最终审查与验证各一次，报告实际URL和证据；不自动提交、推送、PR或发布。
