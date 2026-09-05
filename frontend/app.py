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
            language = st.selectbox("Language", languages, key="submit_language")
            code = st.text_area(
                "Code",
                value=default_code_template(language),
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
                else:
                    st.error(result.msg)

else:
    st.info("This page will be implemented in the next frontend stage.")