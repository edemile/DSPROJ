import json
import boto3
import pymysql
import pandas as pd
import io
from datetime import datetime

# S3 + RDS CONFIGURATION
BUCKET_NAME = "raw-food-logs"
NUTRITION_CSV = "nutrition_facts.csv"

RDS_HOST = "nutrition-database.cqdcmmewsh2e.us-east-1.rds.amazonaws.com"
RDS_USER = "admin"
RDS_PASSWORD = "J26u4403!"
RDS_DB = "nutrition_tracker"

def lambda_handler(event, context):
    try:
        # 1. Get the S3 object key from the event
        s3_key = event['Records'][0]['s3']['object']['key']
        s3 = boto3.client("s3")

        # 2. Download .xlsx food log from S3
        file_obj = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        food_log = pd.read_excel(io.BytesIO(file_obj['Body'].read()))
        food_log.columns = food_log.columns.str.strip().str.lower()

        # 3. Load local nutrition_facts.csv from S3
        nutrition_obj = s3.get_object(Bucket=BUCKET_NAME, Key=NUTRITION_CSV)
        nutrition_df = pd.read_csv(io.BytesIO(nutrition_obj['Body'].read()))
        nutrition_df.columns = nutrition_df.columns.str.strip().str.lower()
        nutrition_df = nutrition_df.rename(columns={
            "irom": "iron", "sugars": "sugar", "carbohydrate": "carbohydrates"
        })

        # 4. Merge and compute
        merged = pd.merge(food_log, nutrition_df, on="name")
        merged["date"] = pd.to_datetime(merged["date"])
        nutrient_cols = [
            "calories", "total_fat", "sodium", "calcium", "iron", "potassium",
            "protein", "carbohydrates", "fiber", "sugar", "water"
        ]

        for col in nutrient_cols:
            merged[col] = (merged[col] * merged["amount"]) / 100

        summary = merged.groupby("date")[nutrient_cols].sum().reset_index()

        # 5. Insert into RDS
        conn = pymysql.connect(
            host=RDS_HOST,
            user=RDS_USER,
            password=RDS_PASSWORD,
            database=RDS_DB,
            cursorclass=pymysql.cursors.DictCursor
        )

        with conn.cursor() as cursor:
            for _, row in summary.iterrows():
                cursor.execute("""
                    INSERT INTO nutrient_log (
                        log_date, calories, total_fat, sodium, calcium, iron,
                        potassium, protein, carbohydrates, fiber, sugar, water
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    row['date'], row['calories'], row['total_fat'], row['sodium'], row['calcium'],
                    row['iron'], row['potassium'], row['protein'], row['carbohydrates'],
                    row['fiber'], row['sugar'], row['water']
                ))
        conn.commit()
        conn.close()

        return {
            'statusCode': 200,
            'body': json.dumps("Successfully processed and inserted into RDS.")
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }
