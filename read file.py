import pandas as pd
import ast
import re

def fix_apostrophes(s):
    return re.sub(r"(\w)'s\b", r"\1’s", s)

df = pd.read_csv("SEntFiN.csv")

rows = []
skipped_rows = []
skipped_entities = []
fixed_count = 0

for _, row in df.iterrows():
    title = row["Title"]
    raw = row["Decisions"]

    try:
        decisions = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        try:
            decisions = ast.literal_eval(fix_apostrophes(raw))
            fixed_count += 1
        except (ValueError, SyntaxError):
            skipped_rows.append((row["S No."], title, raw))
            continue

    for entity, sentiment in decisions.items():
        entity_clean = entity.replace("’", "'")
        if entity_clean not in title:
            skipped_entities.append((row["S No."], title, entity_clean))
            continue
        tgt_sentence = title.replace(entity_clean, "[TGT]", 1)
        rows.append({"sentence": tgt_sentence, "sentiment": sentiment})

out_df = pd.DataFrame(rows)
out_df.to_csv("SEntFiN_tgt.csv", index=False)

print(f"Wrote {len(out_df)} rows")
print(f"Fixed {fixed_count} rows via apostrophe repair")