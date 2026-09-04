# IceteaOJ

程序设计训练 Python 实验二 Step 1：题目管理。

## 运行

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

启动后访问 `http://127.0.0.1:8000/docs` 查看接口文档。

## 测试

```bash
pytest -q
```

## 已实现接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/health` | 健康检查 |
| `GET` | `/api/problems/` | 查看题目列表 |
| `POST` | `/api/problems/` | 添加题目 |
| `GET` | `/api/problems/{problem_id}` | 查看题目信息 |
| `PUT` | `/api/problems/{problem_id}` | 编辑题目 |
| `DELETE` | `/api/problems/{problem_id}` | 删除题目 |

题目文件默认保存在 `data/problems/`。所有响应都使用课程要求的 `code`、`msg`、`data` 结构。

Step 1 暂不实现登录与管理员权限；完成 Step 4 时我们会给这些接口接入统一鉴权。

