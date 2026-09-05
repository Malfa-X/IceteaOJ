import json
import streamlit as st

from api_client import ApiClient


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"


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
        return None, f"Invalid JSON: {error}"

def reset_api_client() -> None:
    st.session_state.api_client = ApiClient(st.session_state.api_base_url)

def default_problem_payload() -> dict:
    return {
        "id": "P1001",
        "title": "A+B Problem",
        "description": "Calculate a + b.",
        "input_description": "Two integers a and b.",
        "output_description": "The sum of a and b.",
        "samples": [{"input": "1 2", "output": "3"}],
        "constraints": "|a|, |b| <= 10^9",
        "testcases": [
            {"input": "1 2", "output": "3"},
            {"input": "-2 5", "output": "3"},
        ],
        "hint": "",
        "source": "",
        "tags": ["basic"],
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

st.set_page_config(
    page_title="IceteaOJ",
    page_icon="OJ",
    layout="wide",
)

st.title("IceteaOJ")

with st.sidebar:
    st.subheader("Backend")
    st.text_input(
        "API Base URL",
        key="api_base_url",
        value=DEFAULT_API_BASE_URL,
        on_change=reset_api_client,
    )

    page = st.radio(
        "Page",
        [
            "Health",
            "Account",
            "Users",
            "Problems",
            "Submissions",
            "Logs",
            "AI Authoring",
        ],
    )

client = get_api_client()
current_user = st.session_state.get("current_user")
if current_user:
    st.sidebar.success(f"Logged in as {current_user['username']} ({current_user['role']})")
else:
    st.sidebar.warning("Not logged in")

if page == "Health":
    st.header("Health Check")

    if st.button("Check backend"):
        result = client.get("/api/health")
        if result.ok:
            st.success(result.msg)
            st.json(result.data)
        else:
            st.error(result.msg)

elif page == "Account":
    st.header("Account")

    login_tab, register_tab, profile_tab = st.tabs(["Login", "Register", "Profile"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login")

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
                st.success("Login success")
            else:
                st.error(result.msg)

        if st.button("Logout"):
            result = client.post("/api/auth/logout")
            st.session_state.pop("current_user", None)
            if result.ok:
                st.success("Logout success")
            else:
                st.error(result.msg)

    with register_tab:
        with st.form("register_form"):
            username = st.text_input("Username", key="register_username")
            password = st.text_input("Password", type="password", key="register_password")
            submitted = st.form_submit_button("Register")

        if submitted:
            result = client.post(
                "/api/users/",
                json={
                    "username": username,
                    "password": password,
                },
            )
            if result.ok:
                st.success("Register success")
                st.json(result.data)
            else:
                st.error(result.msg)

    with profile_tab:
        current_user = st.session_state.get("current_user")
        if not current_user:
            st.info("Please login first.")
        elif st.button("Load my profile"):
            result = client.get(f"/api/users/{current_user['user_id']}")
            if result.ok:
                st.json(result.data)
            else:
                st.error(result.msg)

elif page == "Users":
    st.header("Users")

    current_user = st.session_state.get("current_user")
    if not current_user:
        st.info("Please login first.")
    elif current_user["role"] != "admin":
        st.warning("Only administrators can manage users.")
    else:
        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader("Load Users")
            page_number = st.number_input("Page", min_value=1, value=1)
            page_size = st.number_input("Page size", min_value=1, value=20)

            if st.button("Refresh users"):
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
                st.caption(f"Total: {users_data['total']}")
                st.dataframe(users_data["users"], use_container_width=True)
            else:
                st.info("Click refresh to load users.")

        st.subheader("Change Role")
        with st.form("role_form"):
            user_id = st.text_input("User ID")
            role = st.selectbox("Role", ["user", "admin", "banned"])
            submitted = st.form_submit_button("Update role")

        if submitted:
            result = client.put(
                f"/api/users/{user_id}/role",
                json={"role": role},
            )
            if result.ok:
                st.success("Role updated")
                st.json(result.data)
            else:
                st.error(result.msg)

elif page == "Problems":
    st.header("Problems")

    current_user = st.session_state.get("current_user")
    if not current_user:
        st.info("Please login first.")
    else:
        list_tab, detail_tab, create_tab, edit_tab, delete_tab = st.tabs(
            ["List", "Detail", "Create", "Edit", "Delete"]
        )

        with list_tab:
            if st.button("Load problems"):
                result = client.get("/api/problems/")
                if result.ok:
                    st.session_state.problems_data = result.data
                else:
                    st.error(result.msg)

            problems_data = st.session_state.get("problems_data")
            if problems_data:
                st.dataframe(problems_data, use_container_width=True)
            else:
                st.info("Click load to fetch problems.")

        with detail_tab:
            problem_id = st.text_input("Problem ID", key="detail_problem_id")
            if st.button("Load problem detail"):
                result = client.get(f"/api/problems/{problem_id}")
                if result.ok:
                    st.json(result.data)
                    st.session_state.last_problem_detail = result.data
                else:
                    st.error(result.msg)

        with create_tab:
            initial_text = json.dumps(
                default_problem_payload(),
                ensure_ascii=False,
                indent=2,
            )
            problem_text = st.text_area(
                "Problem JSON",
                value=initial_text,
                height=420,
                key="create_problem_json",
            )

            if st.button("Create problem"):
                payload, error = parse_json_text(problem_text)
                if error:
                    st.error(error)
                else:
                    result = client.post("/api/problems/", json=payload)
                    if result.ok:
                        st.success("Problem created")
                        st.json(result.data)
                    else:
                        st.error(result.msg)

        with edit_tab:
            problem_id = st.text_input("Problem ID", key="edit_problem_id")

            if st.button("Load problem for editing"):
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
                "Updated Problem JSON",
                value=json.dumps(default_problem_payload(), ensure_ascii=False, indent=2),
                height=420,
                key="edit_problem_text_area",
            )

            if st.button("Update problem"):
                payload, error = parse_json_text(problem_text)
                if error:
                    st.error(error)
                elif payload.get("id") != problem_id:
                    st.error("Path problem id and JSON id must match.")
                else:
                    result = client.put(f"/api/problems/{problem_id}", json=payload)
                    if result.ok:
                        st.success("Problem updated")
                        st.json(result.data)
                    else:
                        st.error(result.msg)

        with delete_tab:
            problem_id = st.text_input("Problem ID", key="delete_problem_id")
            st.warning("Deleting a problem requires administrator permission.")

            if st.button("Delete problem"):
                result = client.delete(f"/api/problems/{problem_id}")
                if result.ok:
                    st.success("Problem deleted")
                    st.json(result.data)
                else:
                    st.error(result.msg)

elif page == "Submissions":
    st.header("Submissions")

    current_user = st.session_state.get("current_user")
    if not current_user:
        st.info("Please login first.")
    else:
        submit_tab, list_tab, detail_tab = st.tabs(["Submit", "List", "Detail"])

        with submit_tab:
            languages_result = client.get("/api/languages/")
            if languages_result.ok:
                languages = languages_result.data["name"]
            else:
                languages = ["python"]
                st.warning(languages_result.msg)

            problem_id = st.text_input("Problem ID", key="submit_problem_id")
            language = st.selectbox(
                "Language",
                languages,
                key="submit_language",
                on_change=reset_submission_code_template,
            )
            if "submit_code" not in st.session_state:
                st.session_state.submit_code = default_code_template(language)

            code = st.text_area(
                "Code",
                height=360,
                key="submit_code",
            )

            if st.button("Submit code"):
                result = client.post(
                    "/api/submissions/",
                    json={
                        "problem_id": problem_id,
                        "language": language,
                        "code": code,
                    },
                )
                if result.ok:
                    st.success("Submission created")
                    st.json(result.data)
                    st.session_state.last_submission_id = result.data["submission_id"]
                else:
                    st.error(result.msg)

        with list_tab:
            st.subheader("Query submissions")

            query_col1, query_col2, query_col3 = st.columns(3)
            with query_col1:
                query_problem_id = st.text_input("Problem ID", key="list_problem_id")
            with query_col2:
                query_status = st.selectbox(
                    "Status",
                    ["", "pending", "success", "error"],
                    key="list_status",
                )
            with query_col3:
                page_size = st.number_input("Page size", min_value=1, value=20)

            if st.button("Load submissions"):
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
                st.caption(f"Total: {submissions_data['total']}")
                st.dataframe(submissions_data["submissions"], use_container_width=True)
            else:
                st.info("Click load to fetch submissions.")

        with detail_tab:
            default_submission_id = st.session_state.get("last_submission_id", "")
            submission_id = st.text_input(
                "Submission ID",
                value=default_submission_id,
                key="detail_submission_id",
            )

            if st.button("Load submission detail"):
                result = client.get(f"/api/submissions/{submission_id}")
                if result.ok:
                    data = result.data
                    st.session_state.last_submission_id = data["submission_id"]
                    st.session_state.submission_detail_data = data
                else:
                    st.error(result.msg)

            data = st.session_state.get("submission_detail_data")
            if data:
                st.metric("Status", data["status"])

                if data["status"] != "pending":
                    score_col, counts_col = st.columns(2)
                    score_col.metric("Score", data.get("score"))
                    counts_col.metric("Counts", data.get("counts"))

                    st.subheader("Compile Info")
                    compile_info = data.get("compile_info")
                    if compile_info is None:
                        st.info("No compile info.")
                    else:
                        st.json(compile_info)

                    st.subheader("Run Info")
                    run_info = data.get("run_info")
                    if run_info is None:
                        st.info("No run info.")
                    else:
                        st.json(run_info)

                    st.subheader("Error Info")
                    st.write(data.get("error_info") or "")

                    if st.button("Load submission log"):
                        log_result = client.get(
                            f"/api/submissions/{data['submission_id']}/log"
                        )
                        if log_result.ok:
                            st.subheader("Submission Log")
                            st.metric("Log Score", log_result.data["score"])
                            st.metric("Log Counts", log_result.data["counts"])
                            st.dataframe(
                                log_result.data["details"],
                                use_container_width=True,
                            )
                        else:
                            st.error(log_result.msg)

elif page == "Logs":
    st.header("Logs")

    current_user = st.session_state.get("current_user")
    if not current_user:
        st.info("Please login first.")
    else:
        submission_log_tab, visibility_tab, access_log_tab = st.tabs(
            ["Submission Log", "Log Visibility", "Access Audit"]
        )

        with submission_log_tab:
            st.subheader("View submission judge log")
            st.caption(
                "Users can view their own logs. Other users can view logs only when "
                "the problem has public cases enabled. Admins can view all logs."
            )

            default_submission_id = st.session_state.get("last_submission_id", "")
            submission_id = st.text_input(
                "Submission ID",
                value=default_submission_id,
                key="log_submission_id",
            )

            if st.button("Load judge log"):
                result = client.get(f"/api/submissions/{submission_id}/log")
                if result.ok:
                    st.session_state.last_submission_id = submission_id
                    st.metric("Score", result.data["score"])
                    st.metric("Counts", result.data["counts"])
                    st.dataframe(result.data["details"], use_container_width=True)
                else:
                    st.error(result.msg)

        with visibility_tab:
            st.subheader("Update problem log visibility")
            st.caption("This action requires administrator permission.")

            with st.form("log_visibility_form"):
                problem_id = st.text_input(
                    "Problem ID",
                    key="visibility_problem_id",
                )
                public_cases = st.checkbox(
                    "Allow other users to view this problem's submission logs",
                    key="visibility_public_cases",
                )
                submitted = st.form_submit_button("Update visibility")

            if submitted:
                result = client.put(
                    f"/api/problems/{problem_id}/log_visibility",
                    json={"public_cases": public_cases},
                )
                if result.ok:
                    st.success("Log visibility updated")
                    st.json(result.data)
                else:
                    st.error(result.msg)

        with access_log_tab:
            st.subheader("Query log access records")
            st.caption("This page is only available to administrators.")

            filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
            with filter_col1:
                user_id = st.text_input("User ID", key="access_log_user_id")
            with filter_col2:
                problem_id = st.text_input("Problem ID", key="access_log_problem_id")
            with filter_col3:
                page_number = st.number_input(
                    "Page",
                    min_value=1,
                    value=1,
                    key="access_log_page",
                )
            with filter_col4:
                page_size = st.number_input(
                    "Page size",
                    min_value=1,
                    value=20,
                    key="access_log_page_size",
                )

            if st.button("Load access logs"):
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
    st.header("AI Problem Authoring")

    current_user = st.session_state.get("current_user")
    if not current_user:
        st.info("Please login first.")
    else:
        config_tab, create_tab, status_tab = st.tabs(
            ["Model Config", "Create Task", "Task Status"]
        )

        with config_tab:
            st.subheader("Model configuration")
            st.caption(
                "Only administrators can change model settings. The API key is never "
                "returned in plain text."
            )

            if current_user["role"] != "admin":
                st.warning("Only administrators can manage AI model configuration.")
            else:
                if st.button("Load current AI config"):
                    result = client.get("/api/ai/config")
                    if result.ok:
                        st.json(result.data)
                    else:
                        st.error(result.msg)

                with st.form("ai_config_form"):
                    provider_url = st.text_input(
                        "Provider URL",
                        value="mock://local",
                        key="ai_provider_url",
                    )
                    model_name = st.text_input(
                        "Model name",
                        value="mock-problem-generator",
                        key="ai_model_name",
                    )
                    api_key = st.text_input(
                        "API key",
                        value="mock-api-key",
                        type="password",
                        key="ai_api_key",
                    )
                    input_price = st.number_input(
                        "Input price per 1K tokens",
                        min_value=0.0,
                        value=0.0,
                        step=0.0001,
                        format="%.6f",
                        key="ai_input_price",
                    )
                    output_price = st.number_input(
                        "Output price per 1K tokens",
                        min_value=0.0,
                        value=0.0,
                        step=0.0001,
                        format="%.6f",
                        key="ai_output_price",
                    )
                    submitted = st.form_submit_button("Save AI config")

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
                        st.success("AI config saved")
                        st.json(result.data)
                    else:
                        st.error(result.msg)

        with create_tab:
            st.subheader("Create an AI problem task")

            with st.form("ai_task_form"):
                topic = st.text_input(
                    "Topic",
                    value="loop and arithmetic",
                    key="ai_task_topic",
                )
                difficulty = st.selectbox(
                    "Difficulty",
                    ["easy", "medium", "hard"],
                    key="ai_task_difficulty",
                )
                testcase_count = st.number_input(
                    "Testcase count",
                    min_value=1,
                    max_value=20,
                    value=5,
                    key="ai_task_testcase_count",
                )
                requirements = st.text_area(
                    "Requirements",
                    value="Generate a beginner friendly programming problem.",
                    height=140,
                    key="ai_task_requirements",
                )
                submitted = st.form_submit_button("Start AI authoring")

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
                    st.success("AI authoring task started")
                    st.code(task["task_id"])
                else:
                    st.error(result.msg)

        with status_tab:
            st.subheader("Task status and generated problem")

            default_task_id = st.session_state.get("last_ai_task_id", "")
            task_id = st.text_input(
                "AI task ID",
                value=default_task_id,
                key="ai_status_task_id",
            )

            status_col, cancel_col, apply_col = st.columns(3)
            with status_col:
                if st.button("Refresh AI task"):
                    result = client.get(f"/api/ai/tasks/{task_id}")
                    if result.ok:
                        st.session_state.last_ai_task_id = task_id
                        st.session_state.ai_task_data = result.data
                    else:
                        st.error(result.msg)

            with cancel_col:
                if st.button("Cancel AI task"):
                    result = client.put(f"/api/ai/tasks/{task_id}/cancel")
                    if result.ok:
                        st.session_state.ai_task_data = result.data
                        st.warning("AI task cancelled")
                    else:
                        st.error(result.msg)

            with apply_col:
                if st.button("Apply generated problem"):
                    result = client.post(f"/api/ai/tasks/{task_id}/apply")
                    if result.ok:
                        st.success("Generated problem added to problem repository")
                        st.json(result.data)
                    else:
                        st.error(result.msg)

            task = st.session_state.get("ai_task_data")
            if task:
                st.metric("Status", task["status"])
                st.progress(task["progress"] / 100)
                st.write(task.get("message") or "")

                if task.get("error_info"):
                    st.error(task["error_info"])

                usage = task.get("token_usage")
                if usage:
                    st.subheader("Token usage and estimated cost")
                    usage_col1, usage_col2, usage_col3 = st.columns(3)
                    usage_col1.metric("Input tokens", usage["input_tokens"])
                    usage_col2.metric("Output tokens", usage["output_tokens"])
                    usage_col3.metric(
                        "Total cost",
                        f"{usage['total_cost']} {usage['currency']}",
                    )
                    st.caption(usage.get("pricing_note") or "")

                generated_problem = task.get("result")
                if generated_problem:
                    st.subheader("Generated problem JSON")
                    st.json(generated_problem)

                    st.session_state.create_problem_json = json.dumps(
                        generated_problem,
                        ensure_ascii=False,
                        indent=2,
                    )
                    st.info(
                        "The generated JSON has also been copied into the Problems "
                        "page create form state. You can review it there before saving."
                    )
            else:
                st.info("Start a task or enter an existing AI task ID, then refresh.")

else:
    st.info("This page will be implemented in the next frontend stage.")
