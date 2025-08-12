import streamlit as st
import pandas as pd
import json
import os
import time
from pathlib import Path
from datetime import datetime

# --- CONFIG ---
DATA_DIR = Path("data")
RESPONSES_DIR = Path("responses")

st.set_page_config(page_title="Vergleiche", layout="centered")

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

# --- Persist responses locally (ephemeral on Streamlit Cloud) ---
RESPONSES_DIR.mkdir(exist_ok=True, parents=True)
response_path = RESPONSES_DIR / f"{token_id}_responses.csv"

# unified schema (works even if an older file exists)
resp_cols = [
    "pair_id", "sentence_A", "sentence_B",
    "winner", "loser", "label", "weight",
    "unknown_term", "timestamp"
]
if response_path.exists():
    df_responses = pd.read_csv(response_path)
    for c in resp_cols:
        if c not in df_responses.columns:
            df_responses[c] = pd.NA
    df_responses = df_responses[resp_cols]
else:
    df_responses = pd.DataFrame(columns=resp_cols)

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

def record_choice_from_slider(choice_idx: int, unknown_term: bool):
    labels = ["auf jeden Fall A", "eher A", "eher B", "auf jeden Fall B"]
    weights = [1.0, 0.6, 0.6, 1.0]  # tweak if needed
    winner_map = ["A", "A", "B", "B"]

    label = labels[choice_idx]
    winner_side = winner_map[choice_idx]
    if winner_side == "A":
        winner, loser = current["sentence_A"], current["sentence_B"]
    else:
        winner, loser = current["sentence_B"], current["sentence_A"]

    new_row = {
        "pair_id": current["pair_id"],
        "sentence_A": current["sentence_A"],
        "sentence_B": current["sentence_B"],
        "winner": winner,
        "loser": loser,
        "label": label,
        "weight": weights[choice_idx],
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
    st.info(f"Bitte zuerst lesen … Auswahl erscheint in {remaining}s.")
    time.sleep(1)
    st.rerun()
else:
    # ---- Confidence slider + submit ----
    labels = ["auf jeden Fall A", "eher A", "eher B", "auf jeden Fall B"]
    choice_idx = st.slider(
        "Wie sicher bist du in deiner Entscheidung?",
        min_value=0, max_value=3, value=1, step=1, format="%d"
    )
    # show the textual label under the slider
    st.caption(f"Auswahl: **{labels[choice_idx]}**")

    unknown = st.checkbox("⚑ Unbekanntes Wort/Begriff in diesem Paar")

    # Submit button
    if st.button("Antwort speichern"):
        record_choice_from_slider(choice_idx, unknown)
