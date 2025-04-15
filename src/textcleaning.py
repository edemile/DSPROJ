import pandas as pd
import os


file_path = os.path.expanduser("~/Desktop/4300/master_file.csv")
df = pd.read_csv(file_path)

# clean up column names 
df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(r"[^\w\s]", "", regex=True)
    .str.replace(r"\s+", "_", regex=True)
)

# columns to keep
desired_cols = [
    "name", "serving_size", "calories", "total_fat", "sodium", "calcium", "irom",
    "potassium", "protein", "carbohydrate", "fiber", "sugars", "water"
]

# filter to only the desired columns
df = df[[col for col in desired_cols if col in df.columns]]

# function to clean numeric columns (remove units)
def clean_column(column):
    if column.dtype == "object":
        # Remove non-numeric characters like 'g', 'mg', '%', etc.
        cleaned = column.replace(r"[^\d\.]", "", regex=True)
        return pd.to_numeric(cleaned, errors='coerce')
    return column

# apply cleaning function to relevant columns
for col in df.columns:
    if col not in ['name', 'serving_size']:
        df[col] = clean_column(df[col])

# check for missing data after cleaning
missing_data_after_cleaning = df.isna().sum()
print("\nMissing values after cleaning:")
print(missing_data_after_cleaning)

# drop rows without 'name'
df.dropna(subset=['name'], inplace=True)

# preview cleaned data--- double check before saving
print("\nCleaned dataset preview:")
print(df.head())

# saving
df.to_csv("~/Desktop/4300/nutrition_facts.csv", index=False)