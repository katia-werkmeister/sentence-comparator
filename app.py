import streamlit as st
import pandas as pd
import json
import os
from urllib.parse import parse_qs

# --- CONFIG ---
DATA_DIR = "data"
RESPONSES_DIR = "responses"
NUM_TOTAL_TASKS = 40

# --- Get RA ID from URL ---
query_params = st.experimental_get_query_params()
ra_id = query_params.get("user", [None])[0]

st.set_page_config(page_title="Sentence Comparison Task", layout="centered")

# --- Load task data ---
if not ra_id:
    st.error("Please provide your RA ID via the URL (e.g., ?user=RA1).")
    st.stop()

task_file = f"{DATA_DIR}/{ra_id}.json"
if not os.path.exists(task_file):
    st.error(f"No task file found for user: {ra_id}")
    st.stop()

with open(task_file, "r", encoding="utf-8") as f:
    task_data = [json.loads(line) for line in f]

df_tasks = pd.DataFrame(task_data)
df_tasks["index"] = range(1, len(df_tasks) + 1)

# --- Load progress (if exists) ---
response_path = f"{RESPONSES_DIR}/{ra_id}_responses.csv"
if os.path.exists(response_path):
    df_responses = pd.read_csv(response_path)
else:
    df_responses = pd.DataFrame(columns=["pair_id", "sentence_A", "sentence_B", "choice"])

# --- Determine next unanswered task ---
answered_pairs = set(df_responses["pair_id"])
remaining_df = df_tasks[~df_tasks["pair_id"].isin(answered_pairs)]

if len(remaining_df) == 0:
    st.success("🎉 You have completed all 40 comparisons!")
    st.download_button("Download your responses", df_responses.to_csv(index=False), file_name=f"{ra_id}_responses.csv")
    st.markdown("📧 Please email your downloaded file to **werkmeister@ifo.de**. Thank you!")
    st.stop()

current_task = remaining_df.iloc[0]

# --- Display comparison task ---
st.title("Sentence Comparison Task")
st.markdown(f"**RA ID:** `{ra_id}`")
st.markdown(f"**Progress:** {len(answered_pairs)}/40\n")

st.markdown(f"### {current_task['index']}. Which sentence is better?")
st.write("**Sentence A**")
st.info(current_task["sentence_A"])
st.write("**Sentence B**")
st.info(current_task["sentence_B"])

# --- Record response ---
def record_choice(choice):
    new_row = {
        "pair_id": current_task["pair_id"],
        "sentence_A": current_task["sentence_A"],
        "sentence_B": current_task["sentence_B"],
        "choice": choice
    }
    df_responses_updated = pd.concat([df_responses, pd.DataFrame([new_row])], ignore_index=True)
    df_responses_updated.to_csv(response_path, index=False)
    st.experimental_rerun()

st.write("#### Your choice:")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Sentence A is better"):
        record_choice("A")
with col2:
    if st.button("Sentence B is better"):
        record_choice("B")
with col3:
    if st.button("Not sure"):
        record_choice("Not sure")
