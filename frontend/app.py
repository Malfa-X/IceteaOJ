import streamlit as st

from api_client import ApiClient


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"


def get_api_client() -> ApiClient:
    if "api_client" not in st.session_state:
        st.session_state.api_client = ApiClient(
            st.session_state.get("api_base_url", DEFAULT_API_BASE_URL)
        )

    return st.session_state.api_client


def reset_api_client() -> None:
    st.session_state.api_client = ApiClient(st.session_state.api_base_url)


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

else:
    st.info("This page will be implemented in the next frontend stage.")