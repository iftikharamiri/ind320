import streamlit as st

from modules.feedback_ui import render_sidebar

st.set_page_config(page_title="IND320", layout="wide")

render_sidebar()

st.title("IND320 - Data to Decision")
