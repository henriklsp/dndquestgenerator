"""
app.py — Streamlit web UI for the D&D Quest Generator.

Layout (two-column, no sidebar):
  Left column  — image, controls, attribution
  Right column — output (hint / spinner / generated scenario)

On wide screens (desktop, landscape phone) the columns sit side by side.
On narrow screens (portrait phone) Streamlit stacks them: controls above output.
"""

import streamlit as st
import streamlit.components.v1 as components
import html
import json

from dndgenerator import generate_scenario


# ---------------------------------------------------------------------------
# Page config — must be the first Streamlit call in the script.
# layout="wide" lets the output column fill comfortable reading width.
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

/* Left controls column — fixed width so it doesn't grow too wide on very wide screens */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
    flex: 0 0 280px !important;
    max-width: 280px !important;
    background-color: rgb(50, 30, 50) !important;
    border-radius: 6px;
    padding: 0 1rem 1rem 1rem !important;
}

/* Padding above the image so it doesn't touch the top of the panel */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child img {
    margin-top: 1rem;
}

/* Input fields — dark gray background with black border */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child input {
    background-color: #1b111b !important;
    border: 2px solid #000000 !important;
    color: #ffffff !important;
}

/* Center-align the Generate Quest button */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stButton"] {
    text-align: center;
}

/* White text for input labels, markdown paragraphs, and the info box in the left column */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child label,
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child p {
    color: #ffffff !important;
}

/* Soften the horizontal rule so it blends with the dark background */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child hr {
    border-color: rgba(255, 255, 255, 0.3) !important;
}
</style>
""", unsafe_allow_html=True)


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
# Page title — spans full width above both columns
# ---------------------------------------------------------------------------
st.title("D&D Quest Generator")

# ---------------------------------------------------------------------------
# Two-column layout
# [1, 2] ratio: controls get ~1/3, output gets ~2/3 of page width.
# On narrow screens Streamlit stacks the columns vertically (controls first).
# ---------------------------------------------------------------------------
col_controls, col_output = st.columns([1, 2])


# ---------------------------------------------------------------------------
# Left column — image, controls, attribution
# ---------------------------------------------------------------------------
with col_controls:
    st.image("dragonimg.png", use_container_width=True)

    level = st.number_input("Level", min_value=1, max_value=20, value=1)

    theme_override = st.text_input("Theme (leave blank for random)")

    # Plain text input — type="password" would trigger browser password managers,
    # which is inappropriate for an API key.
    api_key = st.text_input("Your Mistral API key")
    st.info(
        "Leave the API key blank to use the default mistral-tiny AI model. "
        "For better results, use your own API key.\n\n"
        "[Get Key](https://docs.mistral.ai/getting-started/quickstart)"
    )

    generate_clicked = st.button("Generate Quest")

    st.markdown("---")
    st.markdown("*Created by Henrik Schou-Pedersen*")


# ---------------------------------------------------------------------------
# Right column — generation and output
# generate_clicked is set in the left column but is a plain Python variable,
# so it is readable here without any special handling.
# ---------------------------------------------------------------------------
with col_output:

    # --- Generation ---
    # Streamlit reruns the entire script on every interaction, so the button
    # guard ensures generation only runs when the button is actually clicked.
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

    # --- Error display ---
    # Show any error from the last generation run in red, just below the spinner.
    if st.session_state.get("error"):
        st.markdown(
            f'<p style="color:#cc0000;">{html.escape(st.session_state["error"])}</p>',
            unsafe_allow_html=True,
        )

    # --- Output ---
    if "scenario" not in st.session_state or not st.session_state["scenario"]:
        # Hint shown before first generation (or after a fatal error)
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
