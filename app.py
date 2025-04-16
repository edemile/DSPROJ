
import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Nutrition Tracker", layout="wide")
st.title("🥗 Nutrition Progress Tracker")
st.markdown("Upload a food log (Excel) to calculate and visualize your nutrient intake over time.")

# Upload user Excel file
uploaded_file = st.file_uploader("📤 Upload your food log (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        user_df = pd.read_excel(uploaded_file)
        user_df.columns = user_df.columns.str.strip().str.lower()

        if not {"date", "name", "amount"}.issubset(user_df.columns):
            st.error("Excel must have columns: 'date', 'name', 'amount'")
        else:
            # Load nutrition data
            nutrition_df = pd.read_csv("nutrition_facts.csv")
            nutrition_df.columns = nutrition_df.columns.str.strip().str.lower()
            nutrition_df = nutrition_df.rename(columns={"irom": "iron"})

            # Merge user data with nutrition data
            merged = pd.merge(user_df, nutrition_df, on="name")
            merged["date"] = pd.to_datetime(merged["date"])

            # Scale nutrients based on amount
            nutrient_cols = [col for col in merged.columns if col not in {"name", "serving_size", "date", "amount"}]
            for col in nutrient_cols:
                merged[col] = (merged[col] * merged["amount"]) / 100

            # Aggregate by day
            summary = merged.groupby("date")[nutrient_cols].sum().reset_index()

            # Show data
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
        st.error(f"Something went wrong: {e}")
