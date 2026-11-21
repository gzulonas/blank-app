import streamlit as st

from reverse_vowels import Solution, VOWELS_EN, VOWELS_LT

st.set_page_config(page_title="Reverse Vowels", page_icon="🔤", layout="centered")

solution = Solution()

VOWEL_SETS = {
    "English (a e i o u)": VOWELS_EN,
    "Lithuanian (+ ą ę ė į ų ū y)": VOWELS_LT,
}

st.title("🔤 Reverse Vowels")
st.caption(
    "Two rules for the same idea: consonants, spaces and punctuation never "
    "move, only the vowels do."
)

text = st.text_input("Text", value="beautiful house")

col_a, col_b = st.columns([2, 1])
with col_a:
    set_name = st.selectbox("Vowel set", list(VOWEL_SETS.keys()))
with col_b:
    min_len = st.number_input(
        "Min cluster length", min_value=1, max_value=5, value=2,
        help="Version 2 only moves vowel runs at least this long. "
             "At 1 it behaves like version 1 on single letters.",
    )

vowels = VOWEL_SETS[set_name]

if not text:
    st.info("Type something above to see both versions.")
    st.stop()

# ---------------- Results ----------------

v1 = solution.reverseVowels(text, vowels)
v2 = solution.reverseSpokenVowels(text, vowels, min_len)

left, right = st.columns(2)
with left:
    st.subheader("Version 1")
    st.caption("Every vowel is movable")
    st.code(v1, language=None)
with right:
    st.subheader("Version 2")
    st.caption("Only clusters of %d+ are movable" % min_len)
    st.code(v2, language=None)
    if v2 == text:
        st.caption("↑ unchanged — fewer than two clusters to swap")

# ---------------- What the algorithm sees ----------------

runs = solution.vowelRuns(text, vowels)
clusters = [r for r in runs if r[1] - r[0] >= min_len]
lone = [r for r in runs if r[1] - r[0] < min_len]


def highlight(s, picked):
    """Render s with the picked runs marked and the rest dimmed."""
    out = []
    prev = 0
    for start, end, body in picked:
        out.append(s[prev:start].replace(" ", "&nbsp;"))
        out.append("<mark>%s</mark>" % body.replace(" ", "&nbsp;"))
        prev = end
    out.append(s[prev:].replace(" ", "&nbsp;"))
    return "<div style='font-family:monospace;font-size:1.1rem'>%s</div>" % "".join(out)


st.divider()
st.subheader("What the algorithm sees")

st.markdown("**Movable clusters** (version 2 swaps these)")
if clusters:
    st.markdown(highlight(text, clusters), unsafe_allow_html=True)
    st.write(
        "in order: "
        + " → ".join("`%s`" % c[2] for c in clusters)
        + "  ·  reversed: "
        + " → ".join("`%s`" % c[2] for c in reversed(clusters))
    )
else:
    st.write("_none_ — every vowel here stands alone, so version 2 changes nothing.")

st.markdown("**Frozen lone vowels** (version 2 leaves these in place)")
if lone:
    st.markdown(highlight(text, lone), unsafe_allow_html=True)
    st.write(" ".join("`%s`" % l[2] for l in lone))
else:
    st.write("_none_")

with st.expander("Try these"):
    st.markdown(
        "- `ICE` — both vowels stand alone, so version 2 returns it untouched\n"
        "- `beautiful house` — `eau` and `ou` swap\n"
        "- `see you later` — `ee` and `ou` swap\n"
        "- `road trip queue` — `oa` and `ueue` swap\n"
        "- `Ąžuolas` — switch to the Lithuanian set to see the diacritics count\n"
        "\n"
        "Note: version 2 works on letters as written. `ICE` is spoken /aɪs/, "
        "a real diphthong, but English spelling hides it inside one letter — "
        "catching that needs a pronunciation dictionary, not a letter rule."
    )
