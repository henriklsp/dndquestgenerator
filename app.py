import streamlit as st
import streamlit.components.v1 as components
from dndgenerator import generate_scenario

st.title("D&D Quest Generator")

# Sidebar inputs
with st.sidebar:
    level = st.number_input("Level", min_value=1, max_value=20, value=1)
    theme_override = st.text_input("Theme (leave blank for random)")
    api_key = st.text_input("Your Mistral API key", type="password")
    st.info("Your key uses mistral-medium. No key or invalid key falls back to the built-in mistral-tiny (slower, shorter output).")
    generate_clicked = st.button("Generate Quest")

# Run generation only when button is clicked
if generate_clicked:
    with st.spinner("Generating scenario..."):
        scenario, extra = generate_scenario(
            level=level,
            theme_override=theme_override,
            user_key=api_key if api_key else None,
            fallback_key=st.secrets.get("MISTRAL_API_KEY", ""),
        )
    st.session_state["output"] = scenario + "\n\n" + ("=" * 60) + "\n\n" + extra

# Display outputs if available
if "output" in st.session_state:
    st.text_area("Scenario", value=st.session_state["output"], height=800, disabled=True)

    if st.button("Print"):
        components.html("<script>window.print();</script>", height=0)
