"""Collatz exercise: one button, one output.

First press samples a random integer in [1, 100]; every press after that
applies one Collatz step (n/2 if even, 3n+1 if odd) until it reaches 1,
which the Collatz conjecture says always happens.
"""

import random

import streamlit as st

st.title("Collatz-knutis")

# The current integer lives in session state, so it survives reruns.
# `path` keeps every value we have shown, for the celebration chart.
st.session_state.setdefault("value", None)
st.session_state.setdefault("path", [])
st.session_state.setdefault("celebrated", False)


def button_label() -> str:
    n = st.session_state.value
    if n is None:
        return "Start"
    if n == 1:
        return "Play again"
    return "Half it" if n % 2 == 0 else "Triple and add one"


def step() -> None:
    """Advance one Collatz step, or (re)start when there is nothing to step."""
    n = st.session_state.value
    if n is None or n == 1:
        st.session_state.value = random.randint(1, 100)
        st.session_state.path = [st.session_state.value]
        st.session_state.celebrated = False
        return

    st.session_state.value = n // 2 if n % 2 == 0 else 3 * n + 1
    st.session_state.path.append(st.session_state.value)


st.button(button_label(), on_click=step, type="primary")

value = st.session_state.value

if value is None:
    st.write("Ready")
elif value != 1:
    st.write(value)
else:
    # One "u" per step taken, so a long journey earns a longer SIUUU.
    steps = len(st.session_state.path) - 1
    st.title("SU" + "i" * max(3, steps) + "!", text_alignment="center")
    st.caption("⚽ Cristiano Ronaldo approves.", text_alignment="center")

    st.success(
        f"Success! Reached 1 in {steps} steps from {st.session_state.path[0]}. 🐓🐓",
        icon=":material/celebration:",
    )

    # Fire the animation only on the run that first reaches 1, not on every
    # rerun afterwards.
    if not st.session_state.celebrated:
        st.balloons()
        st.toast("SIUUU!", icon="⚽")
        st.session_state.celebrated = True

    with st.container(horizontal=True):
        st.metric("Starting number", st.session_state.path[0])
        st.metric("Steps", len(st.session_state.path) - 1)
        st.metric("Highest point", max(st.session_state.path))

    st.line_chart(st.session_state.path, y_label="Value", x_label="Step")
    st.caption("The whole journey down to 1.")
