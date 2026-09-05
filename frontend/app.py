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
            "Login",
            "Problems",
            "Submissions",
            "Users",
        ],
    )

client = get_api_client()

if page == "Health":
    st.header("Health Check")

    if st.button("Check backend"):
        result = client.get("/api/health")
        if result.ok:
            st.success(result.msg)
            st.json(result.data)
        else:
            st.error(result.msg)

elif page == "Login":
    st.header("Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
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
            st.json(result.data)
        else:
            st.error(result.msg)

    if st.button("Logout"):
        result = client.post("/api/auth/logout")
        st.session_state.pop("current_user", None)
        if result.ok:
            st.success("Logout success")
        else:
            st.error(result.msg)

else:
    st.info("This page will be implemented in the next frontend stage.")