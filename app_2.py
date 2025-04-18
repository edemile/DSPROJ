import streamlit as st
import pandas as pd
import altair as alt
import boto3
import io
from datetime import datetime
import pymysql

# Streamlit layout
st.set_page_config(page_title="Nutrition Tracker", layout="wide")
st.title("🥗 Nutrition Progress Tracker")
st.markdown("Upload a food log (.xlsx) to calculate and visualize your nutrient intake over time.")

# --- AWS + S3 config ---
s3 = boto3.client("s3")
BUCKET_NAME = "raw-food-logs"

# --- RDS connection ---
def get_db_connection():
    return pymysql.connect(
        host="nutrition-database.cqdcmmewsh2e.us-east-1.rds.amazonaws.com",
        user="admin",
        password="J26u4403!",
        database="nutrition_tracker",
        cursorclass=pymysql.cursors.DictCursor
    )

def insert_summary_to_rds(summary_df):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            for _, row in summary_df.iterrows():
                cursor.execute("""
                    INSERT INTO nutrient_log (
                        log_date, calories, total_fat, sodium, calcium, iron,
                        potassium, protein, carbohydrates, fiber, sugar, water
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    row['date'], row['calories'], row['total_fat'], row['sodium'], row['calcium'],
                    row['iron'], row['potassium'], row['protein'], row['carbohydrates'],
                    row['fiber'], row['sugar'], row['water']
                ))
        conn.commit()
        conn.close()
        st.success("✅ Summary saved to RDS")
    except Exception as e:
        st.error(f"❌ Failed to insert into RDS: {e}")

# --- File Upload ---
uploaded_file = st.file_uploader("📤 Upload your food log (.xlsx)", type=["xlsx"])

if uploaded_file:
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    s3_key = f"uploads/user_upload_{timestamp}.xlsx"

    try:
        file_bytes = uploaded_file.read()
        buffer = io.BytesIO(file_bytes)

        # Upload to S3
        s3.upload_fileobj(io.BytesIO(file_bytes), BUCKET_NAME, s3_key)
        st.success(f"✅ File uploaded to S3: `{s3_key}`")

        # Read Excel
        buffer.seek(0)
        user_df = pd.read_excel(buffer)
        user_df.columns = user_df.columns.str.strip().str.lower()

        if not {"date", "name", "amount"}.issubset(user_df.columns):
            st.error("Excel must have columns: 'date', 'name', 'amount'")
        else:
            nutrition_df = pd.read_csv("nutrition_facts.csv")
            nutrition_df.columns = nutrition_df.columns.str.strip().str.lower()

            # Rename problem columns
            nutrition_df = nutrition_df.rename(columns={
                "irom": "iron",
                "sugars": "sugar",
                "carbohydrate": "carbohydrates"
            })

            # Merge
            merged = pd.merge(user_df, nutrition_df, on="name", how="inner")
            merged["date"] = pd.to_datetime(merged["date"])

            nutrient_cols = [
                "calories", "total_fat", "sodium", "calcium", "iron", "potassium",
                "protein", "carbohydrates", "fiber", "sugar", "water"
            ]

            # Double-check existence
            for col in nutrient_cols:
                if col not in merged.columns:
                    st.error(f"Missing expected column in merged data: {col}")
                    st.stop()

            for col in nutrient_cols:
                merged[col] = (merged[col] * merged["amount"]) / 100

            summary = merged.groupby("date")[nutrient_cols].sum().reset_index()

            # Insert to RDS
            insert_summary_to_rds(summary)

            # UI
            st.subheader("📋 Daily Nutrient Totals")
            st.dataframe(summary.style.format(precision=2))

            st.subheader("📈 Nutrient Trends Over Time")
            for col in nutrient_cols:
                st.markdown(f"**{col.capitalize()}**")
                chart = alt.Chart(summary).mark_line(point=True).encode(
                    x='date:T',
                    y=alt.Y(f'{col}:Q', title=col.capitalize()),
                    tooltip=['date', col]
                ).properties(width=700, height=300)
                st.altair_chart(chart, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Something went wrong: {e}")
