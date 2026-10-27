import os

import requests
import streamlit as st


def get_api_url() -> str:
    # Streamlit Cloud: set API_URL in the app's Secrets. Elsewhere: an env var.
    try:
        url = st.secrets["API_URL"]
    except Exception:
        url = os.getenv("API_URL", "http://127.0.0.1:8000")
    return url.rstrip("/")


API_URL = get_api_url()

st.set_page_config(page_title="Notes", page_icon="📝")


# ---------- API helpers ----------
def api(method: str, path: str, **kwargs) -> requests.Response:
    headers = kwargs.pop("headers", {})
    if "token" in st.session_state:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    return requests.request(method, f"{API_URL}{path}", headers=headers, timeout=60, **kwargs)


def error_text(r: requests.Response) -> str:
    try:
        detail = r.json().get("detail")
    except ValueError:
        return r.text
    if isinstance(detail, list):  # FastAPI validation errors
        return "; ".join(f"{e['loc'][-1]}: {e['msg']}" for e in detail)
    return str(detail)


def logout():
    st.session_state.pop("token", None)
    st.session_state.pop("username", None)


# ---------- login / register ----------
def auth_page():
    st.title("📝 Notes")
    login_tab, register_tab = st.tabs(["Log in", "Register"])

    with login_tab:
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log in", type="primary"):
                r = api("POST", "/login", data={"username": username, "password": password})
                if r.ok:
                    st.session_state.token = r.json()["access_token"]
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error(error_text(r))

    with register_tab:
        with st.form("register"):
            username = st.text_input("Username (3-30 characters)")
            password = st.text_input("Password (min 8 characters)", type="password")
            if st.form_submit_button("Create account", type="primary"):
                r = api("POST", "/register", json={"username": username, "password": password})
                if r.status_code == 201:
                    st.success("Account created. Log in on the first tab.")
                else:
                    st.error(error_text(r))


# ---------- notes ----------
def notes_page():
    with st.sidebar:
        st.write(f"Signed in as **{st.session_state.username}**")
        st.button("Log out", on_click=logout)

    st.title("📝 My notes")

    with st.form("new_note", clear_on_submit=True):
        title = st.text_input("Title")
        content = st.text_area("Content")
        if st.form_submit_button("Add note", type="primary"):
            r = api("POST", "/notes", json={"title": title, "content": content})
            if r.status_code == 201:
                st.toast("Note added")
            else:
                st.error(error_text(r))

    r = api("GET", "/notes")
    if r.status_code == 401:  # token expired
        logout()
        st.rerun()
    if not r.ok:
        st.error(error_text(r))
        return

    notes = r.json()
    if not notes:
        st.info("No notes yet. Add one above.")
        return

    for note in reversed(notes):
        with st.expander(note["title"]):
            with st.form(f"edit_{note['id']}"):
                new_title = st.text_input("Title", note["title"])
                new_content = st.text_area("Content", note["content"])
                save, delete = st.columns(2)
                if save.form_submit_button("Save"):
                    r = api("PATCH", f"/notes/{note['id']}",
                            json={"title": new_title, "content": new_content})
                    if r.ok:
                        st.rerun()
                    st.error(error_text(r))
                if delete.form_submit_button("Delete"):
                    r = api("DELETE", f"/notes/{note['id']}")
                    if r.ok:
                        st.rerun()
                    st.error(error_text(r))


try:
    if "token" in st.session_state:
        notes_page()
    else:
        auth_page()
except requests.ConnectionError:
    st.error(f"Can't reach the API at {API_URL}. Is the backend running?")
except requests.Timeout:
    st.warning("The API is waking up (free hosting sleeps when idle). Refresh in a few seconds.")
