from pathlib import Path
import ast
import pandas as pd

root = Path(__file__).parent
for name in ["SEntFiN.csv", "SEntFiN_input.csv", "SEntFiN_output.csv", "SEntFiN_tgt.csv"]:
    path = root / name
    df = pd.read_csv(path)
    print(f"\n{name}: shape={df.shape}")
    print("columns=", list(df.columns))
    print(df.head(3).to_string(index=False))

print("\nSEntFiN_tgt label counts")
tgt = pd.read_csv(root / "SEntFiN_tgt.csv")
print(tgt["sentiment"].value_counts(dropna=False).to_string())

print("\nSEntFiN source decision audit")
src = pd.read_csv(root / "SEntFiN.csv")
rows = []
parse_errors = 0
missing_entities = 0
for _, row in src.iterrows():
    try:
        decisions = ast.literal_eval(row["Decisions"])
    except Exception:
        parse_errors += 1
        continue
    entities = list(decisions.keys())
    missing = [e for e in entities if str(e) not in str(row["Title"])]
    missing_entities += len(missing)
    rows.append({"n_entities": len(entities), "n_missing": len(missing)})
summary = pd.DataFrame(rows)
print("source_rows=", len(src))
print("parse_errors=", parse_errors)
print("rows_parsed=", len(summary))
print("missing_entity_mentions=", missing_entities)
print("entity_count_distribution=")
print(summary["n_entities"].value_counts().sort_index().to_string())
print("source_labels=")
labels = []
for raw in src["Decisions"].dropna():
    try:
        labels.extend(ast.literal_eval(raw).values())
    except Exception:
        pass
print(pd.Series(labels).value_counts().to_string())
