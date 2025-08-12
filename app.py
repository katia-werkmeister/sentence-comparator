import streamlit as st
import pandas as pd
import json
import time
from pathlib import Path
from datetime import datetime

# --- CONFIG ---
DATA_DIR = Path("data")
RESPONSES_DIR = Path("responses")

st.set_page_config(page_title="Vergleiche", layout="centered")

# --- Scoped CSS (timer only) ---
st.markdown("""
<style>
/* Timer box */
.timer-box {
  background:#D6D7F8; color:#131675; padding:16px; border-radius:12px;
  border:2px solid #aeb0f2; text-align:center; font-weight:600;
}
</style>
""", unsafe_allow_html=True)

# --- Read token from URL (?user=TOKEN) ---
token_id = st.query_params.get("user")  # returns str or None
if not token_id:
    st.error("Please provide your RA token via the URL (e.g., ?user=RA1_abcd1234).")
    st.stop()

# --- Resolve JSON file by token ---
task_file = DATA_DIR / f"{token_id}.json"
if not task_file.exists():
    st.error(f"No task file found for token: {token_id}. Please check your link.")
    st.stop()

# --- Load tasks for this token ---
records = []
with open(task_file, "r", encoding="utf-8") as f:
    for line in f:
        records.append(json.loads(line))

df_tasks = pd.DataFrame(records)
df_tasks["index"] = range(1, len(df_tasks) + 1)

# --- Persist responses locally ---
RESPONSES_DIR.mkdir(exist_ok=True, parents=True)
response_path = RESPONSES_DIR / f"{token_id}_responses.csv"

resp_cols = [
    "pair_id", "sentence_A", "sentence_B",
    "winner", "loser", "unknown_term", "timestamp"
]
if response_path.exists():
    df_responses = pd.read_csv(response_path)
    for c in resp_cols:
        if c not in df_responses.columns:
            df_responses[c] = pd.NA
    df_responses = df_responses[resp_cols]
else:
    df_responses = pd.DataFrame(columns=resp_cols)

# ---------------- Welcome Page ----------------
if "started" not in st.session_state:
    st.session_state.started = False

if not st.session_state.started:
    st.title("Vergleiche")
    st.markdown(f"**Token:** `{token_id}`")

    st.markdown("""
    **Willkommen!**

    Ich nenne dir mehrere Paare an Fähigkeiten, die Auszubildende im Rahmen ihrer Ausbildung lernen können.  
    **Entscheide für jedes Paar, welche „offener“ formuliert ist.**  
    Mit „offen“ meinen wir, dass es viele verschiedene Möglichkeiten gibt, diese Fähigkeit anzuwenden.

    Wenn du einen Begriff in einer der Fähigkeiten nicht kennst, kannst du das markieren, indem du auf **„Unbekannter Begriff in diesem Paar“** klickst.

    Wenn du mit allen Paaren durch bist, **lade bitte die .csv herunter** und sende sie per Mail an **werkmeister@ifo.de**.
    """)

    st.markdown("**Beispiele (offenere Fähigkeit fett):**")
    st.markdown("""
    • **Werbeaktionen und Veranstaltungen planen** vs. „Anordnen und Platzieren von Fellen zu Werkstücken nach Wirkungsgrundsätzen“  
    • „chemische Vorgänge bei der Negativ-, Positiv- und Umkehrentwicklung beschreiben“ vs. **betriebliches Warenwirtschaftssystem nutzen**  
    • „Anwenden zeitsparender Nähtechniken“ vs. **Vorbereitende Arbeiten für die Buchhaltung durchführen**
    """)

    if st.button("Los geht’s"):
        st.session_state.started = True
        st.rerun()
    st.stop()

# ---------------- Task Page ----------------
# --- Determine next unanswered task ---
answered = set(df_responses["pair_id"].dropna())
remaining_df = df_tasks[~df_tasks["pair_id"].isin(answered)]

if len(remaining_df) == 0:
    st.success("🎉 Du hast alle Vergleiche abgeschlossen!")
    st.download_button(
        "Lade deine Ergebnisse herunter",
        df_responses.to_csv(index=False),
        file_name=f"{token_id}_responses.csv",
    )
    st.markdown("📧 Bitte sende die heruntergeladene Datei an **werkmeister@ifo.de**.")
    st.stop()

current = remaining_df.iloc[0]

st.title("Vergleiche")
st.markdown(f"**Token:** `{token_id}`")
st.markdown(f"**Fortschritt:** {len(answered)}/{len(df_tasks)}")

st.markdown(f"### {current['index']}. Welche Fähigkeit ist offener formuliert?")
st.write("**Fähigkeit A**")
st.info(current["sentence_A"])
st.write("**Fähigkeit B**")
st.info(current["sentence_B"])

def save_response(winner_side: str, unknown_term: bool):
    if winner_side == "A":
        winner = current["sentence_A"]; loser = current["sentence_B"]
    else:
        winner = current["sentence_B"]; loser = current["sentence_A"]
    new_row = {
        "pair_id": current["pair_id"],
        "sentence_A": current["sentence_A"],
        "sentence_B": current["sentence_B"],
        "winner": winner,
        "loser": loser,
        "unknown_term": bool(unknown_term),
        "timestamp": datetime.utcnow().isoformat()
    }
    updated = pd.concat([df_responses, pd.DataFrame([new_row])], ignore_index=True)
    updated.to_csv(response_path, index=False)
    st.rerun()

# --- 5s unlock timer per pair ---
if st.session_state.get("last_pair_id") != current["pair_id"]:
    st.session_state["last_pair_id"] = current["pair_id"]
    st.session_state["unlock_at"] = time.time() + 5  # 5 seconds from now

remaining = int(max(0, st.session_state["unlock_at"] - time.time()))

if remaining > 0:
    st.markdown(
        f"<div class='timer-box'>⏳ Bitte zuerst lesen.<br>"
        f"Die Auswahl erscheint in <span style='font-size:1.4em;'>{remaining}</span> Sekunden.</div>",
        unsafe_allow_html=True
    )
    time.sleep(1)
    st.rerun()
else:
    unknown = st.checkbox("⚑ Unbekannter Begriff in diesem Paar")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Fähigkeit A ist offener formuliert", use_container_width=True):
            save_response("A", unknown)
    with col2:
        if st.button("Fähigkeit B ist offener formuliert", use_container_width=True):
            save_response("B", unknown)
