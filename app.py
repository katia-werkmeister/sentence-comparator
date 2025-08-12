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

def save_response(choice_label: str, unknown_term: bool):
    weight_map = {
        "auf jeden Fall A": 1.0,
        "eher A": 0.6,
        "eher B": 0.6,
        "auf jeden Fall B": 1.0,
    }
    winner_side = "A" if choice_label in ("auf jeden Fall A", "eher A") else "B"
    winner = current["sentence_A"] if winner_side == "A" else current["sentence_B"]
    loser  = current["sentence_B"] if winner_side == "A" else current["sentence_A"]

    new_row = {
        "pair_id": current["pair_id"],
        "sentence_A": current["sentence_A"],
        "sentence_B": current["sentence_B"],
        "winner": winner,
        "loser": loser,
        "label": choice_label,
        "weight": weight_map[choice_label],
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
    # ---- Always-visible options via select_slider ----
    options = ["auf jeden Fall A", "eher A", "eher B", "auf jeden Fall B"]
    choice_label = st.select_slider(
        "Bitte wähle deine Einschätzung:",
        options=options,
        value="eher A"
    )
    unknown = st.checkbox("⚑ Unbekanntes Wort/Begriff in diesem Paar")

    if st.button("Antwort speichern"):
        save_response(choice_label, unknown)
