# IceteaOJ

IceteaOJ 是程序设计训练 Python 实验二的在线判题系统示例项目。

项目后端使用 FastAPI，前端使用 Streamlit。当前版本已经覆盖题目管理、语言配置、提交判题、用户登录与权限、提交日志、前端操作页面和 Advance AI 智能命题模块。

## 功能概览

- 题目管理：题目列表、详情、创建、编辑、删除
- 用户系统：注册、登录、退出、查看用户、管理员修改角色
- 权限控制：未登录限制、管理员权限、封禁用户限制
- 判题系统：支持 Python 和 C++ 提交，返回 AC、WA、RE、TLE、MLE、CE 等结果
- 提交管理：创建提交、查询提交列表、查看提交详情、重新判题
- 日志系统：查看提交测试点日志、配置公开测试点、管理员查看访问审计
- AI 智能命题：配置模型、创建命题任务、查看进度、中断任务、统计 token 与费用、导入生成题目
- 前端页面：通过 Streamlit 操作主要后端功能

## 环境安装

建议先创建并激活虚拟环境，再安装依赖：

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

如果只使用已有 Python 环境，也可以直接执行：

```bash
pip install -r requirements.txt
```

依赖中固定了 `websockets>=12,<13`，用于避开 `gradio-client`、`streamlit` 对 `websockets` 版本要求不一致的问题。

## 启动后端

```bash
uvicorn app.main:app --reload
```

后端默认地址：

```text
http://127.0.0.1:8000
```

接口文档地址：

```text
http://127.0.0.1:8000/docs
```

## 启动前端

请先启动后端，再打开另一个 Git Bash 终端运行：

```bash
streamlit run frontend/app.py
```

前端启动后，在浏览器中打开 Streamlit 给出的地址即可使用。

## 默认管理员账号

```text
username: admin
password: admintestpassword
```

管理员可以管理题目、用户角色、日志可见性和访问审计。

## AI 智能命题模块

项目包含实验二 Advance 要求的 AI 智能命题功能。

后端接口位于：

```text
/api/ai/config
/api/ai/tasks/
/api/ai/tasks/{task_id}
/api/ai/tasks/{task_id}/cancel
/api/ai/tasks/{task_id}/apply
```

前端入口位于 Streamlit 侧边栏的 `AI Authoring` 页面。

当前仅支持外部 OpenAI-compatible API 配置。项目不提供模拟题目生成器；如果没有可用的外部 API，AI 命题任务会失败并提示用户配置真实可访问的模型接口。

外部 API 配置示例：

```text
provider_url: https://example.com/v1/responses
model_name: your-model-name
api_key: your-api-key
```

后续拿到真实中转站信息后，只需要替换 provider URL、model name 和 API key。代码优先支持 OpenAI-compatible `/responses` 响应格式，也兼容 `/chat/completions` 响应格式。

管理员可以在页面中配置 provider URL、model name、API key 和输入/输出 token 单价。后端返回配置时会对 API key 脱敏，避免明文泄露。

AI 命题任务支持：

- 命题需求输入：知识点、难度、额外要求、测试点数量
- 任务状态查看：pending、running、success、failed、cancelled
- 进度展示：0 到 100 的任务进度
- 中断接口：可取消未完成任务
- Token 与费用统计：`/responses` 使用 `usage.input_tokens` 和 `usage.output_tokens`；`/chat/completions` 使用 `usage.prompt_tokens` 和 `usage.completion_tokens`
- 题目导入：管理员可以将生成的题目保存到题目仓库

## 运行测试

```bash
pytest -q -p no:cacheprovider
```

如果看到 `PytestCollectionWarning`，通常是因为项目模型中存在以 `Test` 开头的类名，例如 `TestCaseStatus`、`TestCaseResult`。这些 warning 不影响功能测试结果。

## 项目结构

```text
app/
  main.py                  FastAPI 应用和 API 路由
  models.py                Pydantic 数据模型
  repository.py            题目数据仓库
  submission_repository.py 提交数据仓库
  users.py                 用户仓库和密码校验
  languages.py             判题语言注册表
  judge.py                 判题执行逻辑
  logs.py                  提交日志和访问审计
  ai_authoring.py          AI 智能命题配置、任务和模拟生成器

frontend/
  app.py                   Streamlit 前端页面
  api_client.py            前端访问后端 API 的客户端封装

tests/
  test_*.py                自动化测试
```

题目 JSON 文件默认保存在：

```text
data/problems/
```

## 常用开发流程

```bash
pytest -q -p no:cacheprovider
git status
git add <files>
git commit -m "<type>: <message>"
git push
```

推荐每完成一个相对独立的阶段提交一次，例如：

```bash
git commit -m "feat: add streamlit frontend module"
```
