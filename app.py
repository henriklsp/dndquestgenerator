"""
app.py — Streamlit web UI for the D&D Quest Generator.

Layout:
  Sidebar  — level, theme, API key, Generate button
  Main     — formatted scenario output, Print and Copy buttons
"""

import streamlit as st
import streamlit.components.v1 as components
import html
import json

from dndgenerator import generate_scenario


# ---------------------------------------------------------------------------
# Page config — must be the first Streamlit call in the script
# layout="wide" lets the output fill the full browser width instead of being
# constrained to Streamlit's default narrow centre column.
# ---------------------------------------------------------------------------
st.set_page_config(layout="wide")


# ---------------------------------------------------------------------------
# Global CSS
# Note: <style> tags work inside st.markdown; <script> tags do NOT —
# React's dangerouslySetInnerHTML strips them silently. All JavaScript must
# go through st.components.v1.html() instead (see button section below).
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* Inherit serif font in the sidebar.
   Applied only to the section element so Streamlit's icon fonts
   (Material Symbols used by the collapse arrow) are not overridden. */
section[data-testid="stSidebar"] {
    font-family: Georgia, 'Times New Roman', serif;
}

/* Force white background everywhere — overrides Streamlit's default gray */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stHeader"],
.main .block-container {
    background-color: #ffffff;
}

/* Spinner — text and animated ring were invisible on white background */
[data-testid="stSpinner"] p {
    color: #444444;
}
[data-testid="stSpinner"] div[role="status"] > div,
[data-testid="stSpinner"] > div > div {
    border-color: #cccccc !important;
    border-top-color: #444444 !important;
}

/* Title */
h1 {
    font-family: Georgia, 'Times New Roman', serif !important;
    color: #000000 !important;
    background-color: #ffffff;
}

/* Output text area */
.quest-output {
    font-family: Georgia, 'Times New Roman', serif;
    white-space: pre-wrap;   /* preserve line breaks from the LLM response */
    line-height: 1.6;
    color: #000000;
    background-color: #ffffff;
    padding: 1rem 0;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar — user inputs
# ---------------------------------------------------------------------------
st.title("D&D Quest Generator")

with st.sidebar:
    st.image("dragonimg.png", use_container_width=True)
    level = st.number_input("Level", min_value=1, max_value=20, value=1)

    theme_override = st.text_input("Theme (leave blank for random)")

    # Plain text input — using type="password" would trigger browser
    # password managers, which is inappropriate for an API key.
    api_key = st.text_input("Your Mistral API key")
    st.markdown("[Get Key](https://docs.mistral.ai/getting-started/quickstart)")
    st.info("Leave API key blank to use the default mistral-tiny AI model. For better results, use your own API key.")

    generate_clicked = st.button("Generate Quest")
    st.markdown("---")
    st.markdown("*Created by Henrik Schou-Pedersen*")


# ---------------------------------------------------------------------------
# Helper: format the first-pass scenario for display
# ---------------------------------------------------------------------------
def format_scenario(text: str) -> str:
    """
    Return HTML where the first line of every paragraph is bold.

    The LLM writes section headings as the first line of a block, separated
    from the next section by a blank line. Bolding those lines makes the
    output much easier to scan.

    html.escape() is called first so that any stray < > & characters in the
    LLM output cannot break the HTML or inject markup.

    Line breaks are emitted as <br> tags rather than raw newlines so that
    Streamlit's Markdown parser cannot misinterpret lines starting with
    "- " or "* " as list items (which would add unwanted spacing).
    """
    escaped = html.escape(text)
    paragraphs = escaped.split('\n\n')
    result = []
    for para in paragraphs:
        lines = para.split('\n')
        if lines and lines[0].strip():
            lines[0] = f'<strong>{lines[0]}</strong>'
        result.append('<br>'.join(lines))
    return '<br><br>'.join(result)


# ---------------------------------------------------------------------------
# Generation — runs only when the button is clicked
# Streamlit reruns the entire script on every interaction, so without the
# button guard every widget change would trigger a slow LLM call.
# ---------------------------------------------------------------------------
if generate_clicked:
    with st.spinner("Generating scenario..."):
        scenario, extra, summary, error = generate_scenario(
            level=level,
            theme_override=theme_override,
            # Pass None (not empty string) so the function's truthiness check works
            user_key=api_key if api_key else None,
            # Built-in fallback key stored in Streamlit Cloud secrets,
            # never committed to the repository.
            fallback_key=st.secrets.get("MISTRAL_API_KEY", ""),
        )
    # Store in session_state so the output survives Streamlit reruns
    # (e.g. when the user clicks Print or Copy without re-generating).
    st.session_state["scenario"] = scenario
    st.session_state["extra"] = extra
    st.session_state["summary"] = summary
    st.session_state["error"] = error

# Show any error from the last generation run in red, just below the spinner
if st.session_state.get("error"):
    st.markdown(
        f'<p style="color:#cc0000;">{html.escape(st.session_state["error"])}</p>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Output display
# ---------------------------------------------------------------------------
if "scenario" not in st.session_state or not st.session_state["scenario"]:
    st.markdown("""
<div class="quest-output" style="color:#888; font-style:italic;">
Press the Generate Quest button to create your scenario.
</div>
""", unsafe_allow_html=True)

elif st.session_state["scenario"]:
    scenario = st.session_state["scenario"]
    extra    = st.session_state["extra"]
    summary  = st.session_state["summary"]
    full_text = summary + "\n\n" + scenario + "\n\n" + ("=" * 60) + "\n\n" + extra

    # Safely embed the full text as a JavaScript string literal.
    # json.dumps() handles quotes and newlines; the replace() calls escape
    # < and > so the string can't break out of a <script> block.
    text_js = json.dumps(full_text).replace('<', r'\u003c').replace('>', r'\u003e')

    # --- Print and Copy buttons ---
    # These must live inside components.html (an iframe) because st.markdown
    # strips onclick attributes and never executes <script> tags.
    #
    # window.parent.print()  → triggers the browser's print dialog on the
    #                          parent page, not just the tiny iframe.
    # navigator.clipboard    → modern async clipboard API (requires HTTPS,
    #                          which Streamlit Cloud provides).
    # execCommand fallback   → older/restricted browsers where clipboard API
    #                          is unavailable.
    components.html(f"""
<style>
* {{ box-sizing: border-box; margin: 0; }}
body {{ padding: 4px 0; font-family: sans-serif; }}
.row {{ display: flex; gap: 8px; }}
button {{
    background: #ff4b4b; color: #fff; border: none;
    padding: 8px 18px; border-radius: 4px; cursor: pointer; font-size: 14px;
}}
button:hover {{ filter: brightness(0.85); }}
</style>
<div class="row">
  <button onclick="window.parent.print()">🖨 Print</button>
  <button id="cb" onclick="copyText()">Copy to clipboard</button>
</div>
<script>
function copyText() {{
    var text = {text_js};
    var btn  = document.getElementById('cb');
    if (navigator.clipboard) {{
        navigator.clipboard.writeText(text)
            .then(function() {{ btn.textContent = '✓ Copied!'; }})
            .catch(function() {{ fallback(text, btn); }});
    }} else {{
        fallback(text, btn);
    }}
}}
function fallback(text, btn) {{
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;left:-9999px';
    document.body.appendChild(ta);
    ta.focus(); ta.select();
    try {{ document.execCommand('copy'); btn.textContent = '✓ Copied!'; }}
    catch(e) {{ btn.textContent = 'Copy failed'; }}
    document.body.removeChild(ta);
}}
</script>
""", height=50)

    # --- Scenario text ---
    # The summary line is shown first in italics, slightly larger.
    # The first response gets bold headings via format_scenario().
    # The second response (extra Q&A) is appended after a divider.
    #
    # Both use <br> tags for line breaks rather than raw \n so that
    # Streamlit's Markdown parser cannot misinterpret lines starting with
    # "- " or "* " as list items (which would add unwanted margins).
    extra_html = "<strong>Extra</strong><br><br>" + html.escape(extra).replace('\n', '<br>')
    st.markdown(f"""
<div class="quest-output">
<p style="font-size:1.15em; font-style:italic; margin:0 0 1em 0;">{html.escape(summary)}</p>
{format_scenario(scenario)}
<br><br>{"=" * 60}<br><br>
{extra_html}
</div>
""", unsafe_allow_html=True)
