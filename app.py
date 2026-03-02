import streamlit as st
import html
from dndgenerator import generate_scenario

st.markdown("""
<style>
.quest-output {
    font-family: Georgia, 'Times New Roman', serif;
    white-space: pre-wrap;
    line-height: 1.6;
    text-align: left;
}
</style>
""", unsafe_allow_html=True)

st.title("D&D Quest Generator")

# Sidebar inputs
with st.sidebar:
    level = st.number_input("Level", min_value=1, max_value=20, value=1)
    theme_override = st.text_input("Theme (leave blank for random)")
    api_key = st.text_input("Your Mistral API key", type="password")
    st.markdown("[Get Key](https://docs.mistral.ai/getting-started/quickstart)")
    st.info("Your key uses mistral-medium. No key or invalid key falls back to the built-in mistral-tiny (slower, shorter output).")
    generate_clicked = st.button("Generate Quest")


def format_scenario(text):
    """Bold the first line of each paragraph (i.e. first line + each line after a blank line)."""
    escaped = html.escape(text)
    paragraphs = escaped.split('\n\n')
    result = []
    for para in paragraphs:
        lines = para.split('\n')
        if lines and lines[0].strip():
            lines[0] = f'<strong>{lines[0]}</strong>'
        result.append('\n'.join(lines))
    return '\n\n'.join(result)


# Run generation only when button is clicked
if generate_clicked:
    with st.spinner("Generating scenario..."):
        scenario, extra = generate_scenario(
            level=level,
            theme_override=theme_override,
            user_key=api_key if api_key else None,
            fallback_key=st.secrets.get("MISTRAL_API_KEY", ""),
        )
    st.session_state["scenario"] = scenario
    st.session_state["extra"] = extra

# Display outputs if available
if "scenario" in st.session_state:
    scenario = st.session_state["scenario"]
    extra = st.session_state["extra"]
    full_text = scenario + "\n\n" + ("=" * 60) + "\n\n" + extra
    clip_text = html.escape(full_text, quote=True)

    st.markdown(f"""
<textarea id="cliptext" style="position:absolute;left:-9999px;width:1px;height:1px;">{clip_text}</textarea>
<div style="display:flex;gap:0.75rem;margin-bottom:0.75rem;">
  <button onclick="window.print()">🖨 Print</button>
  <button onclick="navigator.clipboard.writeText(document.getElementById('cliptext').value).then(()=>this.textContent='✓ Copied!').catch(()=>this.textContent='Failed')">Copy to clipboard</button>
</div>
<div class="quest-output">{format_scenario(scenario)}

{"=" * 60}

{html.escape(extra)}</div>
""", unsafe_allow_html=True)
