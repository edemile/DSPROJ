import streamlit as st
import pandas as pd
import boto3
import os
from io import StringIO

# credentials 
s3 = boto3.client('s3')

BUCKET_NAME = 'raw-food-logs'
PREFIX = 'processed/'

st.title("🍽️ Nutrition Data Dashboard")

# List CSV files 
@st.cache_data
def list_csv_files():
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=PREFIX)
    files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.csv')]
    return files

# Load selected CSV file from S3
@st.cache_data
def load_csv_from_s3(key):
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
    data = obj['Body'].read().decode('utf-8')
    df = pd.read_csv(StringIO(data))
    return df

# Display file options
csv_files = list_csv_files()

if not csv_files:
    st.warning("No CSV files found in S3.")
else:
    selected_file = st.selectbox("Select a processed CSV file:", csv_files)

    if selected_file:
        df = load_csv_from_s3(selected_file)
        st.success(f"Loaded `{selected_file}` successfully!")

        st.subheader("📊 Data Preview")
        st.dataframe(df.head())

        st.subheader("📈 Summary Stats")
        numeric_cols = df.select_dtypes(include='number').columns
        st.write(df[numeric_cols].describe())