import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path

# --- CONFIG ---
DATA_DIR = Path("data")
RESPONSES_DIR = Path("responses")
NUM_TOTAL_TASKS =  len(df)

st.set_page_config(page_title="Vergleiche", layout="centered")

# --- Read token from URL (?user=TOKEN) ---
# Use the non-experimental API
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
if response_path.exists():
    df_responses = pd.read_csv(response_path)
else:
    df_responses = pd.DataFrame(columns=["pair_id", "sentence_A", "sentence_B", "choice"])

# --- Determine next unanswered task ---
answered = set(df_responses["pair_id"])
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
st.markdown(f"**Progress:** {len(answered)}/{NUM_TOTAL_TASKS}")

st.markdown(f"### {current['index']}. Welche Fähigkeit ist offener formuliert?")
st.write("**Fähigkeit A**")
st.info(current["sentence_A"])
st.write("**Fähigkeit B**")
st.info(current["sentence_B"])

def record_choice(choice):
    new_row = {
        "pair_id": current["pair_id"],
        "sentence_A": current["sentence_A"],
        "sentence_B": current["sentence_B"],
        "choice": choice,
    }
    updated = pd.concat([df_responses, pd.DataFrame([new_row])], ignore_index=True)
    updated.to_csv(response_path, index=False)
    st.rerun()

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Fähigkeit A ist offener formuliert"):
        record_choice("A")
with col2:
    if st.button("Fähigkeit B ist offener formuliert"):
        record_choice("B")
with col3:
    if st.button("Not sure"):
        record_choice("Not sure")
