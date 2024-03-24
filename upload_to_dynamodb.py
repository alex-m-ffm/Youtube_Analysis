import boto3
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from io import FileIO
import os
import pickle
import pandas as pd
from decimal import Decimal
import time

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
            print("Quota limit reached. Waiting for remaining time plus buffer...")
            time_to_wait = 65 - (current_time - last_request_time) % 60  # Calculate remaining time plus buffer
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

# Authenticate and create YouTube Reporting API object
def authenticate_youtube_reporting():
    credentials = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets.json',
                scopes=[
                    'https://www.googleapis.com/auth/youtube.readonly',
                    'https://www.googleapis.com/auth/yt-analytics.readonly'
                ]
            )
            credentials = flow.run_local_server(port=8080, prompt='consent')
            with open('token.pickle', 'wb') as f:
                pickle.dump(credentials, f)
    return build('youtubereporting', 'v1', credentials=credentials)

# Main function to process reports
def process_reports(job_id, table_name, composite_key_cols, decimal_cols):
    youtube_reporting = authenticate_youtube_reporting()
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
        print("No items returned for the specified keys.")
        existing_reports = []
    
    new_reports = [report['id'] for report in reports_result['reports'] if report['id'] not in existing_reports]
    
    for report in reports_result['reports']:
        if report['id'] in new_reports:
            local_file = f"reports/{report['id']}.csv"
            download_report(youtube_reporting, report['downloadUrl'], local_file)
            df = pd.read_csv(local_file)
            if not df.empty:
                df['createTime'] = report['createTime']
                df['date'] = convert_date(df['date'])
                df['composite_key'] = df[composite_key_cols].astype(str).agg('_'.join, axis=1)
                for col in decimal_cols:
                    df[col] = df[col].apply(convert_float_to_decimal)
                upload_to_table(df, table_name)

                #when finished upload report to reports table
                table = dynamodb.Table('reports')
                with table.batch_writer() as batch:
                    batch.put_item(Item=report)              
            os.remove(local_file)

# Define jobs with their respective table names, composite key columns, and columns requiring Decimal conversion
jobs = {
    'a7f41b3e-2b81-488d-8ed0-1f8c236e1a54': {
        'table_name': 'channel_basic_a2',
        'composite_key_cols': ['date', 'channel_id', 'video_id', 'live_or_on_demand', 'subscribed_status', 'country_code'],
        'decimal_cols': ['watch_time_minutes', 'average_view_duration_seconds', 'average_view_duration_percentage', 
                         'red_watch_time_minutes']
    },
    '4a7e6f19-e49f-4418-9800-f0ba979a8437': {
        'table_name': 'channel_demographics_a1',
        'composite_key_cols': ['date', 'channel_id', 'video_id', 'live_or_on_demand', 
                               'subscribed_status', 'country_code', 'age_group', 'gender'],
        'decimal_cols': ['views_percentage']
    },
    'bff80780-0f0f-4caa-af3e-de968ec64e9e': {
        'table_name': 'channel_sharing_service_a1',
        'composite_key_cols': ['date', 'channel_id', 'video_id', 'live_or_on_demand', 
                               'subscribed_status', 'country_code', 'sharing_service'],
        'decimal_cols': ['shares']
    },
    '82bc9b78-afbf-470e-8c1f-e9a7d2fe280d': {
        'table_name': 'channel_combined_a2',
        'composite_key_cols': ['date', 'channel_id', 'video_id', 'live_or_on_demand', 
                               'subscribed_status', 'country_code', 'playback_location_type', 
                               'traffic_source_type', 'device_type', 'operating_system'],
        'decimal_cols': ['views', 'watch_time_minutes', 'average_view_duration_seconds', 
                         'average_view_duration_percentage', 'red_views', 'red_watch_time_minutes']
    }
}

# Process reports for each job
for job_id, params in jobs.items():
    process_reports(job_id, params['table_name'], params['composite_key_cols'], params['decimal_cols'])
