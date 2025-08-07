import pandas as pd
import random
import os
import json
from itertools import combinations
from collections import defaultdict

# ---- PARAMETERS ----
file_path = "df_cluster.dta"      # Your dataset
text_column = "cluster_task"      # Column name for sentence
num_ras = 6
num_total_pairs = 100
num_shared_pairs = 10
sentences_to_sample = 200
output_folder = "data"

# ---- Load and Sample Sentences ----
df = pd.read_stata(file_path)
sentences = df[text_column].dropna().drop_duplicates().sample(n=sentences_to_sample, random_state=42).tolist()

# ---- Create Unique Sentence Pairs ----
all_pairs = list(combinations(sentences, 2))
random.seed(42)
random.shuffle(all_pairs)
selected_pairs = all_pairs[:num_total_pairs]

pairs_df = pd.DataFrame(selected_pairs, columns=["sentence_A", "sentence_B"])
pairs_df["pair_id"] = [f"P{str(i+1).zfill(3)}" for i in range(len(pairs_df))]

# ---- Assign Pairs to RAs ----
shared_pairs = pairs_df.iloc[:num_shared_pairs].copy()
shared_pair_ids = shared_pairs["pair_id"].tolist()
remaining_pairs = pairs_df.iloc[num_shared_pairs:].copy()
remaining_pair_ids = remaining_pairs["pair_id"].tolist()

# Assign each of the 90 remaining pairs to a unique pair of RAs
ra_names = [f"RA{i+1}" for i in range(num_ras)]
ra_combinations = list(combinations(ra_names, 2))
random.shuffle(ra_combinations)
assert len(remaining_pair_ids) <= len(ra_combinations), "Not enough unique RA pairs for remaining sentence pairs."

pair_ra_map = dict(zip(remaining_pair_ids, ra_combinations[:len(remaining_pair_ids)]))

# Create per-RA assignments
assignments = defaultdict(list)
for pair_id, (ra1, ra2) in pair_ra_map.items():
    assignments[ra1].append(pair_id)
    assignments[ra2].append(pair_id)

# Add shared pairs to all RAs
for ra in ra_names:
    assignments[ra].extend(shared_pair_ids)

# ---- Save JSON Files ----
os.makedirs(output_folder, exist_ok=True)

for ra in ra_names:
    ra_pair_ids = assignments[ra]
    ra_df = pairs_df[pairs_df["pair_id"].isin(ra_pair_ids)].copy()
    ra_df = ra_df.sample(frac=1, random_state=42).reset_index(drop=True)  # Randomize order

    records = ra_df.to_dict(orient="records")
    with open(os.path.join(output_folder, f"{ra}.json"), "w", encoding="utf-8") as f:
        for row in records:
            json.dump(row, f, ensure_ascii=False)
            f.write("\n")

print(f"✅ JSON files created in '{output_folder}' folder.")
