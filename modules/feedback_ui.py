"""Sidebar feedback form. Import and call `render_sidebar()` from any page."""

from __future__ import annotations

import hmac

import streamlit as st

from modules.feedback import FeedbackError, Inbox

TOPICS = [
    "General / app",
    "Part 1",
    "Part 2",
    "Part 3",
    "Part 4",
    "Notebooks",
    "Repository / README",
]

_SETUP_HINT = (
    "Add a `[feedback]` section to `.streamlit/secrets.toml` with `password`, "
    "`token` and `repo`."
)


def _config():
    try:
        return st.secrets["feedback"]
    except Exception:
        return None


def _unlock(config) -> bool:
    """Shared-password gate. Returns True once this session is unlocked."""
    if st.session_state.get("feedback_unlocked"):
        return True

    expected = config.get("password", "")
    if not expected:
        st.warning("No feedback password is set.", icon=":material/lock:")
        return False

    with st.form("feedback_unlock", clear_on_submit=True, border=False):
        entered = st.text_input("Password", type="password")
        if st.form_submit_button("Unlock", icon=":material/lock_open:"):
            if hmac.compare_digest(entered, expected):
                st.session_state["feedback_unlocked"] = True
                st.rerun()
            else:
                st.error("Wrong password.", icon=":material/error:")
    return False


def _form(config) -> None:
    with st.form("feedback_form", clear_on_submit=True, border=False):
        topic = st.selectbox("Topic", TOPICS)
        message = st.text_area(
            "Feedback",
            height=140,
            placeholder="What should be fixed, added or explained better?",
        )
        author = st.text_input("Your name", placeholder="Optional")
        submitted = st.form_submit_button(
            "Send", icon=":material/send:", type="primary"
        )

    if not submitted:
        return
    if not message.strip():
        st.warning("Write something first.", icon=":material/edit_note:")
        return

    try:
        with st.spinner("Sending..."):
            Inbox.from_config(config).submit(topic, message, author)
    except FeedbackError as exc:
        st.error(str(exc), icon=":material/error:")
        return

    st.success("Thanks, feedback received.", icon=":material/check_circle:")


def render_sidebar() -> None:
    """Render the feedback form in the sidebar of the current page."""
    with st.sidebar:
        with st.expander("Send feedback", icon=":material/rate_review:"):
            config = _config()
            if config is None:
                st.info("Feedback is not configured yet.", icon=":material/info:")
                st.caption(_SETUP_HINT)
                return
            st.caption("For the teaching assistant. Goes straight to the repo.")
            if _unlock(config):
                _form(config)
