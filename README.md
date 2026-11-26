# LangGraph 学生成绩查询助手

Python 3.12 + LangGraph + LangChain + MySQL + Streamlit。独立于Dify运行，不需要下载框架源码。

## 启动

```bash
cd /Users/silent/Developer/playground/langgraph-school-demo
uv sync --frozen
uv run streamlit run app.py
```

打开 http://127.0.0.1:8502 。停止：运行服务的终端按 Ctrl+C。

## 配置

复制 `.env.example` 为 `.env`，本地填写 `MODEL_API_KEY`、`MODEL_BASE_URL`、`MODEL_NAME`、`DATABASE_URL`。不要提交或分享 `.env`。通义兼容接口默认北京地域，其他地域的Key需要对应的端点。
仅允许读取 `school_demo.student_grades`。账号只能有SELECT权限，禁止用root。云端模型会收到问题、必要表结构及查询结果（每条最多200行，每次最多10条，合计最多2,000行）；数据库密码不会发给模型。

## 正式项目文档

- [设计](docs/superpowers/specs/2026-11-26-school-query-design.md)
- [实施计划](docs/superpowers/plans/2026-11-26-school-query-demo.md)
- [实施记录](docs/implementation-log.md)
- [验收结果](docs/acceptance-report.md)

## 原理

输入检查 → 生成SQL → AST校验 → 只读查询 → 答案汇总。可修复错误反馈给生成节点，最多修正2次；危险查询或连接权限错误直接结束。LangChain封装模型接口，LangGraph控制状态和条件边，数据库查询由本地Python执行。

每次提问独立查询，界面的历史只用于展示；如要追问请写完整条件。未指定学期时统计全部记录；人数按学号去重，及格60、优秀90；排名保留并列。图表只使用查询结果，不让模型生成数值。

## 验证

```bash
uv run pytest -q
uv run python scripts/acceptance.py
```

单元测试使用隔离夹具，不修改学生表。真实验收调用已配置模型并实时读取MySQL，将查询结果与独立基准SQL比较；会消耗少量模型API额度。

## 边界

Demo仅本机访问；不包含登录、多租户、跨轮指代解析或生产部署。不修改MySQL数据/权限。SQL校验不能替代只读账号。每条查询5秒超时，最多展示200行；结果截断和部分失败均显式提示。
