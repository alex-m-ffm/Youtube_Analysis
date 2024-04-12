import boto3
from botocore.exceptions import ClientError
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from io import FileIO
import os
import json
import pandas as pd
from decimal import Decimal
import time
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global variables to track the last request time and the number of requests made in the last minute
last_request_time = 0
requests_in_last_minute = 0

# Function to track API requests and wait if approaching quota limit
def track_and_wait():
    global last_request_time, requests_in_last_minute
    current_time = time.time()
    if current_time - last_request_time < 60:
        requests_in_last_minute += 1
        if requests_in_last_minute >= 60:
            time_to_wait = 75 - round(current_time - last_request_time) % 60  # Calculate remaining time plus buffer
            print(f"Quota limit reached. Waiting for {time_to_wait} seconds...")
            time.sleep(time_to_wait)
            last_request_time = current_time + time_to_wait  # Update last request time
            requests_in_last_minute = 0
            print("Resuming...")
        else:
            last_request_time = current_time
    else:
        last_request_time = current_time
        requests_in_last_minute = 0

# Function to download report from YouTube Reporting API
def download_report(youtube_reporting, report_url, local_file):
    track_and_wait()
    request = youtube_reporting.media().download(resourceName='')
    request.uri = report_url
    with FileIO(local_file, mode='wb') as fh:
        downloader = MediaIoBaseDownload(fh, request, chunksize=-1)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

# Function to convert date from YYYYMMDD format to ISO 8601 format
def convert_date(date_series):
    return pd.to_datetime(date_series, format='%Y%m%d').dt.strftime('%Y-%m-%dT%H:%M:%SZ')

# Function to convert float columns to Decimal and quantize to two decimal places
def convert_float_to_decimal(value):
    if isinstance(value, float):
        return Decimal(value).quantize(Decimal('0.01'))
    else:
        return value

# Function to upload data to DynamoDB
def upload_to_table(df, table_name):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    with table.batch_writer() as batch:
        for _, row in df.iterrows():
            item = row.to_dict()
            batch.put_item(Item=item)

# Function to retrieve OAuth credentials from AWS Secrets Manager
def get_oauth_secret():
    secret_name = os.environ.get('OAuth_Secret_Name')
    region_name = os.environ.get('AWS_Region')

    # Create a Secrets Manager client
    client = boto3.client('secretsmanager', region_name=region_name)

    # Retrieve the secret value
    response = client.get_secret_value(SecretId=secret_name)
    secret_dict = json.loads(response['SecretString'])

    return secret_dict

# Function to retrieve OAuth credentials from AWS Secrets Manager
def get_oauth_token():
    secret_name = os.environ.get('OAuth_Token_Name')
    region_name = os.environ.get('AWS_Region')

    # Create a Secrets Manager client
    client = boto3.client('secretsmanager', region_name=region_name)

    # Retrieve the secret value
    response = client.get_secret_value(SecretId=secret_name)
    secret_dict = json.loads(response['SecretString'])

    return secret_dict

# Function to authenticate with YouTube Reporting API using OAuth credentials
def authenticate_youtube_reporting():
    credentials = None

    credentials_dict = get_oauth_token()

    # Check if the credentials are available in the Secrets Manager
    if 'token' in credentials_dict and 'refresh_token' in credentials_dict:
        credentials = Credentials.from_authorized_user_info(credentials_dict)

        # Check if the credentials are expired
        if credentials.expired:
            # Refresh the credentials
            credentials.refresh(Request())

            # Store the new credentials in Secrets Manager
            secret_name = os.environ.get('OAuth_Token_Name')
            region_name = os.environ.get('AWS_Region')

            client = boto3.client('secretsmanager', region_name=region_name)
            client.put_secret_value(SecretId=secret_name, SecretString=credentials.to_json())
    else:
        # If credentials are not available, initiate the authentication flow
        client_secret = get_oauth_secret()
        flow = InstalledAppFlow.from_client_config(
            client_secret,
            scopes=[
                'https://www.googleapis.com/auth/youtube.readonly',
                'https://www.googleapis.com/auth/yt-analytics.readonly'
            ]
        )
        credentials = flow.run_local_server(port=8080, prompt='consent')

        # Store the new credentials in Secrets Manager
        secret_name = os.environ.get('OAuth_Token_Name')
        region_name = os.environ.get('AWS_Region')
        client = boto3.client('secretsmanager', region_name=region_name)
        client.put_secret_value(SecretId=secret_name, SecretString=credentials.to_json())
        
    # Build and return the YouTube Reporting API object
    youtube_reporting = build('youtubereporting', 'v1', credentials=credentials)
    return youtube_reporting

# Main function to process reports
def process_reports(job_id, table_name, composite_key_cols, decimal_cols):
    track_and_wait()
    reports_result = youtube_reporting.jobs().reports().list(jobId=job_id).execute()

    dynamodb = boto3.resource('dynamodb')

    available_report_ids = [report['id'] for report in reports_result['reports']]
    ids_to_retrieve = [{'id': key} for key in available_report_ids]

    response = dynamodb.batch_get_item(
    RequestItems={
        'reports': {
            'Keys': ids_to_retrieve
            }
            }
    )

    # Check if any items are returned
    if 'Responses' in response:
        items = response['Responses']['reports']
        existing_reports = [item['id'] for item in items]
    else:
        logger.info("No items returned for the specified keys.")
        existing_reports = []
    
    new_reports = [report['id'] for report in reports_result['reports'] if report['id'] not in existing_reports]
    
    for report in reports_result['reports']:
        if report['id'] in new_reports:
            local_file = f"/tmp/{report['id']}.csv"
            download_report(youtube_reporting, report['downloadUrl'], local_file)
            #logger.info(f"Report {report['id']} downloaded successfully.")
            df = pd.read_csv(local_file)
            if not df.empty:
                #logger.info(f"Processing DataFrame for report {report['id']}...")
                df['createTime'] = report['createTime']
                df['date'] = convert_date(df['date'])
                df['video_id'] = df['video_id'].astype(str)
                df['composite_key'] = df[composite_key_cols].astype(str).agg('_'.join, axis=1)
                for col in decimal_cols:
                    df[col] = df[col].apply(convert_float_to_decimal)
                #logger.info(f"Preprocessing DataFrame for report {report['id']} done.")
                upload_to_table(df, table_name)
                #logger.info(f"Report {report['id']} uploaded to DynamoDB table {table_name}.")

                #when finished upload report to reports table
                table = dynamodb.Table('reports')
                with table.batch_writer() as batch:
                    batch.put_item(Item=report)
                logger.info(f"Report {report['id']} processed and uploaded successfully.")
            #else:
                #logger.info(f"No data found in report {report['id']}. Skipping processing.")
            # Remove the file after processing
            os.remove(local_file)
            #logger.info(f"Temporary file {local_file} removed.")
    logger.info(f"Processing of Reports for {table_name} completed.")              

#initiate the connection
youtube_reporting = authenticate_youtube_reporting()

def lambda_handler(event, context):
    # Access the jobs dictionary from the event payload
    jobs = event.get('jobs', {})

    logger.info('Hello! I will now retrieve and process your YouTube reports!')

    # Process reports for each job
    for job_id, params in jobs.items():
        try:
            # Your code logic here
            process_reports(job_id, params['table_name'], params['composite_key_cols'], params['decimal_cols'])

        except Exception as e:
            logger.exception('An error occurred:')
            raise  # Re-raise the exception to ensure Lambda handles it

    return { 
        'message' : 'Reports retrieved and new ones loaded to DynamoDB.'
    }
