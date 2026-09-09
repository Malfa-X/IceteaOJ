import json
import streamlit as st

from api_client import ApiClient


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"


PAGE_OPTIONS = [
    "Health",
    "Account",
    "Users",
    "Problems",
    "Submissions",
    "Logs",
    "AI Authoring",
]

PAGE_LABELS = {
    "Health": "🩺 健康检查",
    "Account": "👤 账号",
    "Users": "🛡️ 用户管理",
    "Problems": "📚 题目管理",
    "Submissions": "🚀 提交评测",
    "Logs": "📋 评测日志",
    "AI Authoring": "✨ AI 智能命题",
}

PAGE_DESCRIPTIONS = {
    "Health": "检查后端服务是否正常可用。",
    "Account": "登录、注册并查看当前用户信息。",
    "Users": "管理员管理用户账号与角色权限。",
    "Problems": "创建、查看、编辑和删除编程题目。",
    "Submissions": "提交代码、查询记录并查看评测结果。",
    "Logs": "查看提交日志、可见性设置和访问审计记录。",
    "AI Authoring": "通过可配置 AI 任务生成题目草稿。",
}

STATUS_LABELS = {
    "pending": "等待处理",
    "running": "运行中",
    "success": "已完成",
    "error": "异常",
    "failed": "失败",
    "cancelled": "已中断",
}

def get_api_client() -> ApiClient:
    if "api_client" not in st.session_state:
        st.session_state.api_client = ApiClient(
            st.session_state.get("api_base_url", DEFAULT_API_BASE_URL)
        )

    return st.session_state.api_client

def parse_json_text(text: str) -> tuple[dict | None, str | None]:
    try:
        return json.loads(text), None
    except json.JSONDecodeError as error:
        return None, f"JSON 格式错误: {error}"

def reset_api_client() -> None:
    st.session_state.api_client = ApiClient(st.session_state.api_base_url)

def default_problem_payload() -> dict:
    return {
        "id": "P1001",
        "title": "A+B 问题",
        "description": "给定两个整数 a 和 b，请计算它们的和。",
        "input_description": "输入包含两个整数 a 和 b。",
        "output_description": "输出一个整数，表示 a + b 的结果。",
        "samples": [{"input": "1 2", "output": "3"}],
        "constraints": "|a|, |b| <= 10^9",
        "testcases": [
            {"input": "1 2", "output": "3"},
            {"input": "-2 5", "output": "3"},
        ],
        "hint": "",
        "source": "",
        "tags": ["基础"],
        "time_limit": 1.0,
        "memory_limit": 128,
        "author": "",
        "difficulty": "easy",
        "public_cases": False,
    }

def default_code_template(language: str) -> str:
    if language == "cpp":
        return """#include <iostream>
using namespace std;

int main() {
    long long a, b;
    cin >> a >> b;
    cout << a + b << endl;
    return 0;
}
"""
    return "a, b = map(int, input().split())\nprint(a + b)\n"

def reset_submission_code_template() -> None:
    language = st.session_state.submit_language
    st.session_state.submit_code = default_code_template(language)


def use_external_api_template() -> None:
    st.session_state.ai_provider_url = "https://example.com/v1/responses"
    st.session_state.ai_model_name = "your-model-name"
    st.session_state.ai_api_key = "your-api-key"
    st.session_state.ai_input_price = 0.0
    st.session_state.ai_output_price = 0.0


def apply_theme() -> None:
    st.markdown(
        """
        <style>
            .main .block-container {
                padding-top: 2rem;
                padding-bottom: 3rem;
                max-width: 1180px;
            }

            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
            }

            [data-testid="stSidebar"] * {
                color: #e5e7eb;
            }

            [data-testid="stSidebar"] input {
                color: #111827;
            }

            .app-hero {
                padding: 1.6rem 1.8rem;
                border-radius: 1.2rem;
                background:
                    radial-gradient(circle at top left, rgba(59, 130, 246, 0.26), transparent 30%),
                    linear-gradient(135deg, #111827 0%, #1e3a8a 52%, #0369a1 100%);
                color: white;
                margin-bottom: 1.4rem;
                box-shadow: 0 18px 45px rgba(15, 23, 42, 0.18);
            }

            .app-hero h1 {
                font-size: 2.25rem;
                margin: 0 0 0.35rem 0;
                letter-spacing: -0.03em;
            }

            .app-hero p {
                margin: 0;
                color: #dbeafe;
                font-size: 1rem;
            }

            .soft-card {
                padding: 1rem 1.15rem;
                border: 1px solid #e5e7eb;
                border-radius: 1rem;
                background: #ffffff;
                box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
                margin-bottom: 1rem;
            }

            div[data-testid="stMetric"] {
                background: #f8fafc;
                border: 1px solid #e5e7eb;
                border-radius: 0.9rem;
                padding: 0.8rem;
            }

            .stButton > button {
                border-radius: 0.7rem;
                border: 1px solid #2563eb;
                background: #2563eb;
                color: white;
            }

            .stButton > button:hover {
                border-color: #1d4ed8;
                background: #1d4ed8;
                color: white;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(page_name: str) -> None:
    st.markdown(
        f"""
        <div class="app-hero">
            <h1>{PAGE_LABELS[page_name]}</h1>
            <p>{PAGE_DESCRIPTIONS[page_name]}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_card(text: str) -> None:
    st.markdown(f'<div class="soft-card">{text}</div>', unsafe_allow_html=True)


def display_status(status: str) -> str:
    return STATUS_LABELS.get(status, status)


st.set_page_config(
    page_title="IceteaOJ",
    page_icon="🧊",
    layout="wide",
)

apply_theme()

st.markdown(
    """
    <div class="app-hero">
        <h1>🧊 IceteaOJ</h1>
        <p>一个集题目管理、提交评测、日志审计和 AI 智能命题于一体的轻量在线评测系统。</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## 🧊 IceteaOJ")
    st.caption("FastAPI 后端 + Streamlit 前端")
    st.divider()

    st.subheader("后端服务")
    st.text_input(
        "API 基础地址",
        key="api_base_url",
        value=DEFAULT_API_BASE_URL,
        on_change=reset_api_client,
    )

    selected_page_label = st.radio(
        "页面",
        [PAGE_LABELS[page] for page in PAGE_OPTIONS],
    )
    page = PAGE_OPTIONS[[PAGE_LABELS[item] for item in PAGE_OPTIONS].index(selected_page_label)]

client = get_api_client()
current_user = st.session_state.get("current_user")
if current_user:
    st.sidebar.success(f"已登录：{current_user['username']}（{current_user['role']}）")
else:
    st.sidebar.warning("未登录")

if page == "Health":
    render_page_header(page)

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("后端", "FastAPI")
    metric_col2.metric("前端", "Streamlit")
    metric_col3.metric("评测", "Python / C++")
    metric_col4.metric("附加", "AI 智能命题")

    render_card(
        "演示完整系统前，可以先用本页快速检查后端连通性。"
        "如果后端返回成功，登录、题目管理和评测页面就可以使用同一个 API 地址。"
        ""
    )

    if st.button("检查后端"):
        result = client.get("/api/health")
        if result.ok:
            st.success(result.msg)
            st.json(result.data)
        else:
            st.error(result.msg)

elif page == "Account":
    render_page_header(page)

    login_tab, register_tab, profile_tab = st.tabs(["登录", "注册", "个人信息"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("用户名", key="login_username")
            password = st.text_input("密码", type="password", key="login_password")
            submitted = st.form_submit_button("登录")

        if submitted:
            result = client.post(
                "/api/auth/login",
                json={
                    "username": username,
                    "password": password,
                },
            )
            if result.ok:
                st.session_state.current_user = result.data
                st.success("登录成功")
            else:
                st.error(result.msg)

        current_user = st.session_state.get("current_user")

        if current_user:
            if st.button("退出登录"):
                result = client.post("/api/auth/logout")
                st.session_state.pop("current_user", None)

                if result.ok:
                    st.success("退出成功")
                else:
                    st.error(result.msg)

    with register_tab:
        with st.form("register_form"):
            username = st.text_input("用户名", key="register_username")
            password = st.text_input("密码", type="password", key="register_password")
            submitted = st.form_submit_button("注册")

        if submitted:
            result = client.post(
                "/api/users/",
                json={
                    "username": username,
                    "password": password,
                },
            )
            if result.ok:
                st.success("注册成功")
                st.json(result.data)
            else:
                st.error(result.msg)

    with profile_tab:
        current_user = st.session_state.get("current_user")
        if not current_user:
            st.info("请先登录。")
        elif st.button("加载我的信息"):
            result = client.get(f"/api/users/{current_user['user_id']}")
            if result.ok:
                st.json(result.data)
            else:
                st.error(result.msg)

elif page == "Users":
    render_page_header(page)

    current_user = st.session_state.get("current_user")
    if not current_user:
        st.info("请先登录。")
    elif current_user["role"] != "admin":
        st.warning("只有管理员可以管理用户。")
    else:
        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader("加载用户")
            page_number = st.number_input("页面", min_value=1, value=1)
            page_size = st.number_input("每页数量", min_value=1, value=20)

            if st.button("刷新用户列表"):
                result = client.get(
                    "/api/users/",
                    params={
                        "page": page_number,
                        "page_size": page_size,
                    },
                )
                if result.ok:
                    st.session_state.users_data = result.data
                else:
                    st.error(result.msg)

        with col2:
            users_data = st.session_state.get("users_data")
            if users_data:
                st.caption(f"总数：{users_data['total']}")
                st.dataframe(users_data["users"], use_container_width=True)
            else:
                st.info("点击刷新以加载用户。")

        st.subheader("修改角色")
        with st.form("role_form"):
            user_id = st.text_input("用户 ID")
            role = st.selectbox("角色", ["user", "admin", "banned"])
            submitted = st.form_submit_button("更新角色")

        if submitted:
            result = client.put(
                f"/api/users/{user_id}/role",
                json={"role": role},
            )
            if result.ok:
                st.success("角色已更新")
                st.json(result.data)
            else:
                st.error(result.msg)

elif page == "Problems":
    render_page_header(page)

    current_user = st.session_state.get("current_user")
    if not current_user:
        st.info("请先登录。")
    else:
        list_tab, detail_tab, create_tab, edit_tab, delete_tab = st.tabs(
            ["列表", "详情", "创建", "编辑", "删除"]
        )

        with list_tab:
            if st.button("加载题目列表"):
                result = client.get("/api/problems/")
                if result.ok:
                    st.session_state.problems_data = result.data
                else:
                    st.error(result.msg)

            problems_data = st.session_state.get("problems_data")
            if problems_data:
                st.dataframe(problems_data, use_container_width=True)
            else:
                st.info("点击加载以获取题目。")

        with detail_tab:
            problem_id = st.text_input("题目 ID", key="detail_problem_id")
            if st.button("加载题目详情"):
                result = client.get(f"/api/problems/{problem_id}")
                if result.ok:
                    st.json(result.data)
                    st.session_state.last_problem_detail = result.data
                else:
                    st.error(result.msg)

        with create_tab:
            if "create_problem_json" not in st.session_state:
                st.session_state.create_problem_json = json.dumps(
                    default_problem_payload(),
                    ensure_ascii=False,
                    indent=2,
                )

            problem_text = st.text_area(
                "题目 JSON",
                height=420,
                key="create_problem_json",
            )

            if st.button("创建题目"):
                payload, error = parse_json_text(problem_text)
                if error:
                    st.error(error)
                else:
                    result = client.post("/api/problems/", json=payload)
                    if result.ok:
                        st.success("题目创建成功")
                        st.json(result.data)
                    else:
                        st.error(result.msg)

        with edit_tab:
            problem_id = st.text_input("题目 ID", key="edit_problem_id")

            if st.button("加载题目用于编辑"):
                result = client.get(f"/api/problems/{problem_id}")
                if result.ok:
                    st.session_state.edit_problem_text_area = json.dumps(
                        result.data,
                        ensure_ascii=False,
                        indent=2,
                    )
                else:
                    st.error(result.msg)

            problem_text = st.text_area(
                "更新后的题目 JSON",
                value=json.dumps(default_problem_payload(), ensure_ascii=False, indent=2),
                height=420,
                key="edit_problem_text_area",
            )

            if st.button("更新题目"):
                payload, error = parse_json_text(problem_text)
                if error:
                    st.error(error)
                elif payload.get("id") != problem_id:
                    st.error("路径中的题目 ID 必须和 JSON 中的 id 一致。")
                else:
                    result = client.put(f"/api/problems/{problem_id}", json=payload)
                    if result.ok:
                        st.success("题目更新成功")
                        st.json(result.data)
                    else:
                        st.error(result.msg)

        with delete_tab:
            problem_id = st.text_input("题目 ID", key="delete_problem_id")
            st.warning("删除题目需要管理员权限。")

            if st.button("删除题目"):
                result = client.delete(f"/api/problems/{problem_id}")
                if result.ok:
                    st.success("题目删除成功")
                    st.json(result.data)
                else:
                    st.error(result.msg)

elif page == "Submissions":
    render_page_header(page)

    current_user = st.session_state.get("current_user")
    if not current_user:
        st.info("请先登录。")
    else:
        submit_tab, list_tab, detail_tab = st.tabs(["提交", "列表", "详情"])

        with submit_tab:
            languages_result = client.get("/api/languages/")
            if languages_result.ok:
                languages = languages_result.data["name"]
            else:
                languages = ["python"]
                st.warning(languages_result.msg)

            problem_id = st.text_input("题目 ID", key="submit_problem_id")
            language = st.selectbox(
                "语言",
                languages,
                key="submit_language",
                on_change=reset_submission_code_template,
            )
            if "submit_code" not in st.session_state:
                st.session_state.submit_code = default_code_template(language)

            code = st.text_area(
                "代码",
                height=360,
                key="submit_code",
            )

            if st.button("提交代码"):
                result = client.post(
                    "/api/submissions/",
                    json={
                        "problem_id": problem_id,
                        "language": language,
                        "code": code,
                    },
                )
                if result.ok:
                    st.success("提交创建成功")
                    st.json(result.data)
                    st.session_state.last_submission_id = result.data["submission_id"]
                else:
                    st.error(result.msg)

        with list_tab:
            st.subheader("查询提交记录")

            query_col1, query_col2, query_col3 = st.columns(3)
            with query_col1:
                query_problem_id = st.text_input("题目 ID", key="list_problem_id")
            with query_col2:
                query_status = st.selectbox(
                    "状态",
                    ["", "pending", "success", "error"],
                    key="list_status",
                )
            with query_col3:
                page_size = st.number_input("每页数量", min_value=1, value=20)

            if st.button("加载提交记录"):
                params = {
                    "problem_id": query_problem_id,
                    "page_size": page_size,
                }
                if query_status:
                    params["status"] = query_status

                result = client.get("/api/submissions/", params=params)
                if result.ok:
                    st.session_state.submissions_data = result.data
                else:
                    st.error(result.msg)

            submissions_data = st.session_state.get("submissions_data")
            if submissions_data:
                st.caption(f"总数：{submissions_data['total']}")
                st.dataframe(submissions_data["submissions"], use_container_width=True)
            else:
                st.info("点击加载以获取提交记录。")

        with detail_tab:
            default_submission_id = st.session_state.get("last_submission_id", "")
            submission_id = st.text_input(
                "提交 ID",
                value=default_submission_id,
                key="detail_submission_id",
            )

            detail_col, rejudge_col = st.columns(2)
            with detail_col:
                if st.button("加载提交详情"):
                    result = client.get(f"/api/submissions/{submission_id}")
                    if result.ok:
                        data = result.data
                        st.session_state.last_submission_id = data["submission_id"]
                        st.session_state.submission_detail_data = data
                    else:
                        st.error(result.msg)

            with rejudge_col:
                if current_user["role"] == "admin":
                    if st.button("重新评测该提交"):
                        result = client.put(f"/api/submissions/{submission_id}/rejudge")
                        if result.ok:
                            st.success("重新评测已开始")
                            st.session_state.last_submission_id = result.data[
                                "submission_id"
                            ]
                            st.session_state.submission_detail_data = result.data
                            st.info(
                                "原提交已被重置并重新加入评测队列。"
                                "再次点击“加载提交详情”以刷新结果。"
                            )
                        else:
                            st.error(result.msg)
                else:
                    st.caption("重新评测需要管理员权限。")

            data = st.session_state.get("submission_detail_data")
            if data:
                st.metric("状态", display_status(data["status"]))

                if data["status"] != "pending":
                    score_col, counts_col = st.columns(2)
                    score_col.metric("得分", data.get("score"))
                    counts_col.metric("总分", data.get("counts"))

                    st.subheader("编译信息")
                    compile_info = data.get("compile_info")
                    if compile_info is None:
                        st.info("暂无编译信息。")
                    else:
                        st.json(compile_info)

                    st.subheader("运行信息")
                    run_info = data.get("run_info")
                    if run_info is None:
                        st.info("暂无运行信息。")
                    else:
                        st.json(run_info)

                    st.subheader("错误信息")
                    st.write(data.get("error_info") or "")

                    if st.button("加载提交日志"):
                        log_result = client.get(
                            f"/api/submissions/{data['submission_id']}/log"
                        )
                        if log_result.ok:
                            st.subheader("提交日志")
                            st.metric("日志得分", log_result.data["score"])
                            st.metric("日志总分", log_result.data["counts"])
                            st.dataframe(
                                log_result.data["details"],
                                use_container_width=True,
                            )
                        else:
                            st.error(log_result.msg)

elif page == "Logs":
    render_page_header(page)

    current_user = st.session_state.get("current_user")
    if not current_user:
        st.info("请先登录。")
    else:
        submission_log_tab, visibility_tab, access_log_tab = st.tabs(
            ["提交日志", "日志可见性", "访问审计"]
        )

        with submission_log_tab:
            st.subheader("查看提交评测日志")
            st.caption(
                "用户可以查看自己的日志。其他用户只有在题目公开测试点时才能查看。"
                "管理员可以查看全部日志。"
            )

            default_submission_id = st.session_state.get("last_submission_id", "")
            submission_id = st.text_input(
                "提交 ID",
                value=default_submission_id,
                key="log_submission_id",
            )

            if st.button("加载评测日志"):
                result = client.get(f"/api/submissions/{submission_id}/log")
                if result.ok:
                    st.session_state.last_submission_id = submission_id
                    st.metric("得分", result.data["score"])
                    st.metric("总分", result.data["counts"])
                    st.dataframe(result.data["details"], use_container_width=True)
                else:
                    st.error(result.msg)

        with visibility_tab:
            st.subheader("更新题目日志可见性")
            st.caption("此操作需要管理员权限。")

            with st.form("log_visibility_form"):
                problem_id = st.text_input(
                    "题目 ID",
                    key="visibility_problem_id",
                )
                public_cases = st.checkbox(
                    "允许其他用户查看该题目的提交日志",
                    key="visibility_public_cases",
                )
                submitted = st.form_submit_button("更新可见性")

            if submitted:
                result = client.put(
                    f"/api/problems/{problem_id}/log_visibility",
                    json={"public_cases": public_cases},
                )
                if result.ok:
                    st.success("日志可见性已更新")
                    st.json(result.data)
                else:
                    st.error(result.msg)

        with access_log_tab:
            st.subheader("查询日志访问记录")
            st.caption("此页面仅管理员可用。")

            filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
            with filter_col1:
                user_id = st.text_input("用户 ID", key="access_log_user_id")
            with filter_col2:
                problem_id = st.text_input("题目 ID", key="access_log_problem_id")
            with filter_col3:
                page_number = st.number_input(
                    "页面",
                    min_value=1,
                    value=1,
                    key="access_log_page",
                )
            with filter_col4:
                page_size = st.number_input(
                    "每页数量",
                    min_value=1,
                    value=20,
                    key="access_log_page_size",
                )

            if st.button("加载访问日志"):
                params = {
                    "page": page_number,
                    "page_size": page_size,
                }
                if user_id:
                    params["user_id"] = user_id
                if problem_id:
                    params["problem_id"] = problem_id

                result = client.get("/api/logs/access/", params=params)
                if result.ok:
                    st.dataframe(result.data, use_container_width=True)
                else:
                    st.error(result.msg)

elif page == "AI Authoring":
    render_page_header(page)

    current_user = st.session_state.get("current_user")
    if not current_user:
        st.info("请先登录。")
    else:
        config_tab, create_tab, status_tab = st.tabs(
            ["模型配置", "创建任务", "任务状态"]
        )

        with config_tab:
            st.subheader("模型配置")
            st.caption(
                "只有管理员可以修改模型配置。API key 不会以明文返回。"
                ""
            )

            if current_user["role"] != "admin":
                st.warning("只有管理员可以管理 AI 模型配置。")
            else:
                st.button(
                    "使用外部 API 配置模板",
                    on_click=use_external_api_template,
                )

                st.caption(
                    "请填写符合 OpenAI `/v1/responses` 或 `/v1/chat/completions` 格式的外部接口。"
                    "拿到真实中转站后，替换模型接口地址、模型名称和 API key 即可。"
                )

                if st.button("加载当前 AI 配置"):
                    result = client.get("/api/ai/config")
                    if result.ok:
                        st.json(result.data)
                    else:
                        st.error(result.msg)

                with st.form("ai_config_form"):
                    provider_url = st.text_input(
                        "模型接口地址",
                        value="https://example.com/v1/responses",
                        key="ai_provider_url",
                    )
                    model_name = st.text_input(
                        "模型名称",
                        value="your-model-name",
                        key="ai_model_name",
                    )
                    api_key = st.text_input(
                        "API key",
                        value="your-api-key",
                        type="password",
                        key="ai_api_key",
                    )
                    input_price = st.number_input(
                        "输入每 1K token 价格",
                        min_value=0.0,
                        value=0.0,
                        step=0.0001,
                        format="%.6f",
                        key="ai_input_price",
                    )
                    output_price = st.number_input(
                        "输出每 1K token 价格",
                        min_value=0.0,
                        value=0.0,
                        step=0.0001,
                        format="%.6f",
                        key="ai_output_price",
                    )
                    submitted = st.form_submit_button("保存 AI 配置")

                if submitted:
                    result = client.put(
                        "/api/ai/config",
                        json={
                            "provider_url": provider_url,
                            "model_name": model_name,
                            "api_key": api_key,
                            "input_price_per_1k": input_price,
                            "output_price_per_1k": output_price,
                        },
                    )
                    if result.ok:
                        st.success("AI 配置已保存")
                        st.json(result.data)
                    else:
                        st.error(result.msg)

        with create_tab:
            st.subheader("创建 AI 命题任务")

            with st.form("ai_task_form"):
                topic = st.text_input(
                    "知识点",
                    value="循环与整数运算",
                    key="ai_task_topic",
                )
                difficulty = st.selectbox(
                    "难度",
                    ["简单", "中等", "困难"],
                    key="ai_task_difficulty",
                )
                testcase_count = st.number_input(
                    "测试点数量",
                    min_value=1,
                    max_value=20,
                    value=5,
                    key="ai_task_testcase_count",
                )
                requirements = st.text_area(
                    "命题要求",
                    value="生成一道适合初学者练习的编程题，题面清晰，测试点包含普通情况和边界情况。",
                    height=140,
                    key="ai_task_requirements",
                )
                submitted = st.form_submit_button("开始 AI 命题")

            if submitted:
                result = client.post(
                    "/api/ai/tasks/",
                    json={
                        "topic": topic,
                        "difficulty": difficulty,
                        "requirements": requirements,
                        "testcase_count": testcase_count,
                    },
                )
                if result.ok:
                    task = result.data
                    st.session_state.last_ai_task_id = task["task_id"]
                    st.session_state.ai_task_data = task
                    st.success("AI 命题任务已开始")
                    st.code(task["task_id"])
                else:
                    st.error(result.msg)

        with status_tab:
            st.subheader("任务状态与生成题目")

            default_task_id = st.session_state.get("last_ai_task_id", "")
            task_id = st.text_input(
                "AI 任务 ID",
                value=default_task_id,
                key="ai_status_task_id",
            )

            status_col, cancel_col, apply_col = st.columns(3)
            with status_col:
                if st.button("刷新 AI 任务"):
                    result = client.get(f"/api/ai/tasks/{task_id}")
                    if result.ok:
                        st.session_state.last_ai_task_id = task_id
                        st.session_state.ai_task_data = result.data
                    else:
                        st.error(result.msg)

            with cancel_col:
                if st.button("中断 AI 任务"):
                    result = client.put(f"/api/ai/tasks/{task_id}/cancel")
                    if result.ok:
                        st.session_state.ai_task_data = result.data
                        st.warning("AI 任务已中断")
                    else:
                        st.error(result.msg)

            with apply_col:
                if st.button("导入生成题目"):
                    result = client.post(f"/api/ai/tasks/{task_id}/apply")
                    if result.ok:
                        st.success("生成题目已加入题库")
                        st.json(result.data)
                    else:
                        st.error(result.msg)

            task = st.session_state.get("ai_task_data")
            if task:
                st.metric("状态", display_status(task["status"]))
                st.progress(task["progress"] / 100)
                st.write(task.get("message") or "")

                if task.get("error_info"):
                    st.error(task["error_info"])

                usage = task.get("token_usage")
                if usage:
                    st.subheader("Token 用量与费用估算")
                    usage_col1, usage_col2, usage_col3 = st.columns(3)
                    usage_col1.metric("输入 tokens", usage["input_tokens"])
                    usage_col2.metric("输出 tokens", usage["output_tokens"])
                    usage_col3.metric(
                        "总费用",
                        f"{usage['total_cost']} {usage['currency']}",
                    )
                    st.caption(usage.get("pricing_note") or "")

                generated_problem = task.get("result")
                if generated_problem:
                    st.subheader("生成的题目 JSON")
                    st.json(generated_problem)

                    st.session_state.create_problem_json = json.dumps(
                        generated_problem,
                        ensure_ascii=False,
                        indent=2,
                    )
                    st.info(
                        "生成的 JSON 也已复制到题目管理的创建表单状态中。"
                        "你可以切到题目管理页面审阅后再保存。"
                    )
            else:
                st.info("请先创建任务，或输入已有 AI 任务 ID 后刷新。")

else:
    st.info("此页面将在下一阶段实现。")

