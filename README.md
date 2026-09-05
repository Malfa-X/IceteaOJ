# IceteaOJ

IceteaOJ 是程序设计训练 Python 实验二的在线判题系统示例项目。

项目后端使用 FastAPI，前端使用 Streamlit。当前版本已经覆盖题目管理、语言配置、提交判题、用户登录与权限、提交日志和前端操作页面。

## 功能概览

- 题目管理：题目列表、详情、创建、编辑、删除
- 用户系统：注册、登录、退出、查看用户、管理员修改角色
- 权限控制：未登录限制、管理员权限、封禁用户限制
- 判题系统：支持 Python 和 C++ 提交，返回 AC、WA、RE、TLE、MLE、CE 等结果
- 提交管理：创建提交、查询提交列表、查看提交详情、重新判题
- 日志系统：查看提交测试点日志、配置公开测试点、管理员查看访问审计
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
