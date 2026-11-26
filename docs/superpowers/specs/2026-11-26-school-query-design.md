# LangGraph 学生成绩查询 Demo 设计

状态：用户已于2026-11-26确认，第一版已实现并验证。
项目路径：/Users/silent/Developer/playground/langgraph-school-demo

## 目标与现有依据
在Mac Python3.12上独立运行学生成绩查询Demo，浏览器输入自然语言，实时查询本地MySQL student_grades，展示答案、SQL、数据表、图表和执行步骤，适合面试展示。
已读取用户提供的ifpkg：ZIP内包含manifest.yaml和app.yaml，格式dify.app v2、应用advanced-chat。现有配置描述指向school_demo及600条模拟数据，模型为通义qwen3.8-max，包含SQL生成、迭代查询、结果汇总和柱状/折线/饼图。实际数据库与模型可用性在实现阶段核验，不把导出描述作为已验证状态。
导出文件可作为复现依据，不能直接导入LangGraph运行。不要复制Dify插件和应用运行时。

## 方案取舍
A命令行：最快，但不方便对照Dify演示。
B LangGraph + Streamlit浏览器界面：兼顾学习流程和可交互展示，已按用户确认采用。
C FastAPI + 独立前端：扩展性好，第一版前端工作过多。

## 技术与流程
Python3.12、uv项目内.venv和锁文件；LangGraph StateGraph、LangChain模型适配、SQLAlchemy/PyMySQL、Pydantic、sqlglot、Streamlit、Plotly、pytest。
流程：输入检查 → 生成SQL计划 → AST校验 → 实时查询 → 汇总展示。解析/SQL语法错误进入修正节点，初次后最多修正2次；每次重新校验。连接/权限/危险查询不重试。最多10条直接关联问题的SQL，默认生成最少查询。部分查询失败必须明确披露，不伪装为完整成功。
State保存question、schema、queries、results、errors、repair_count、answer和脱敏trace。首版每次问题独立处理，不承诺指代追问；历史只作显示，不拿旧数据冒充新查询。
模型和API地址可配置，默认参考通义配置，先验证接口能力。优先结构化SQL计划，若不支持则JSON解析加有限纠正。图表仅从真实QueryResult构造，不允许模型补造数字；不适用图表时降级为表格。

## 数据和统计口径
预期字段：id、student_id、student_name、class_name、subject、score、exam_date、semester、grade、created_at、updated_at；启动读取实际schema核对，不建表、不改表、不写数据。
未指定学期按全部成绩记录；人数COUNT(DISTINCT student_id)，记录数COUNT(*)；默认及格60、优秀90，回答说明口径；最高最低默认保留并列，以未ROUND均分排序，最终显示保留2位小数。标签示例依据实际数据，不写死班级或学科。无结果明确说明。

## 执行边界
独立只读账号，只允许student_grades SELECT；先检查授权，若权限过大，提示用户本地准备账号，本Demo不自行修改权限。
SQL AST只允许单条SELECT或只读CTE，表列与函数白名单；拒绝DML/DDL、多语句、系统表/跨库、INTO OUTFILE、锁定查询、SLEEP/BENCHMARK/LOAD_FILE及未知副作用函数。数据库权限不能被模型指令替代。
单条最多展示200行，截断明确标记；不改变聚合的计算范围。MySQL查询超时5秒、连接超时5秒，只读事务结束回滚。
云端模型会收到必要表结构、用户问题和受限查询结果；先确认连接的是模拟数据。秘密从本机.env读取，不发模型，不写Git/日志/截图。缺API配置让用户本地填，不要求在聊天发送Key。
界面默认127.0.0.1:8502，端口冲突明确提示，不影响现有Dify。

## 验收
1. 可一条命令启动中文浏览器界面，显示连接错误且不泄露秘密。
2. 记录数、去重人数、各科均分、最高均分班级、指定学期统计、及格率、分数段分布和无数据，共至少8个真实模型案例，与独立参考SQL结果逐项比较。
3. 并列最高和ROUND陷阱通过独立夹具覆盖，不向用户表插入测试数据。
4. 写操作、跨库、注入、危险函数在执行前拒绝；测试断言执行器未调用。
5. 修正最多2次；超时、认证失败、部分失败和截断明确呈现。
6. 柱/线/饼图标签及数值与查询结果完全对应；不合适数据降级。
7. README说明安装、配置、启动、流程、限制和数据流，给出实际通过数，不把mock通过当成真实模型通过。

## 非目标与确认
不做登录、多租户、任意库访问、数据库写入、生产部署、跨轮指代、多Agent和新增MCP/RAG/Skills。
本设计与实施计划确认后开始实现，不自动提交、推送或发布。
