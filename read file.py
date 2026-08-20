import pandas as pd
import ast
import re

def fix_apostrophes(s):
    return re.sub(r"(\w)'s\b", r"\1’s", s)

df = pd.read_csv("SEntFiN.csv")

input_rows = []
output_rows = []
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

    entities_clean = {e.replace("’", "'"): s for e, s in decisions.items()}

    # verify all entities exist in title before processing this row
    if any(e not in title for e in entities_clean):
        for e in entities_clean:
            if e not in title:
                skipped_entities.append((row["S No."], title, e))
        continue

    for target_entity, sentiment in entities_clean.items():
        masked_title = title
        # mask the target entity
        masked_title = masked_title.replace(target_entity, "Target", 1)
        # mask all other entities as "Other"
        for other_entity in entities_clean:
            if other_entity != target_entity:
                masked_title = masked_title.replace(other_entity, "Other", 1)

        input_rows.append({"sentence": masked_title})
        output_rows.append({
            "sentence": f"The sentiment for Target in the given sentence is {sentiment.upper()}."
        })

input_df = pd.DataFrame(input_rows)
output_df = pd.DataFrame(output_rows)

input_df.to_csv("SEntFiN_input.csv", index=False)
output_df.to_csv("SEntFiN_output.csv", index=False)

print(f"Wrote {len(input_df)} input rows and {len(output_df)} output rows")
print(f"Fixed {fixed_count} rows via apostrophe repair")
print(f"Skipped {len(skipped_rows)} rows with unparseable Decisions")
print(f"Skipped {len(skipped_entities)} entity mentions not found verbatim in title")