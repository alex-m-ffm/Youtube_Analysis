# youtube_api.py

from googleapiclient.discovery import build
from datetime import datetime, timedelta
import re
import pandas as pd

def parse_published_at(published_at_str):
    try:
        # Attempt to parse with the first format including milliseconds
        published_at = datetime.strptime(published_at_str, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        try:
            # Attempt to parse with the second format without milliseconds
            published_at = datetime.strptime(published_at_str, '%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            try:
                # Attempt to parse with the third format including timezone offset
                published_at = datetime.strptime(published_at_str, '%Y-%m-%dT%H:%M:%S%z')
            except ValueError:
                # If parsing fails for all formats, raise an error
                raise ValueError("Invalid 'publishedAt' format")

    # Extract date part without time
    published_date = published_at.date()

    return published_date

def parse_duration(duration_str):

    # Return zero timedelta if duration string is 'P0D'
    if duration_str == 'P0D':
        return timedelta()
    
    # Regular expression pattern to match duration string
    pattern = r'PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?P<seconds>\d+)S?'

    # Match the pattern in the duration string
    match = re.match(pattern, duration_str)

    # Extract hours, minutes, and seconds from the match
    hours = int(match.group('hours')) if match.group('hours') else 0
    minutes = int(match.group('minutes')) if match.group('minutes') else 0
    seconds = int(match.group('seconds')) if match.group('seconds') else 0

    # Calculate total duration in seconds
    total_seconds = hours * 3600 + minutes * 60 + seconds

    return total_seconds

# Define a function to extract hashtags from a string
def extract_hashtags(description):
    # Use regular expression to find all hashtags (words starting with '#')
    hashtags = re.findall(r'#\w+', description)
    return hashtags

def get_channel_data_from_handle(youtube, handle: str):
    request = youtube.channels().list(
        part='id,snippet,statistics,topicDetails,brandingSettings,contentDetails',
        forHandle=handle
    )
    response = request.execute()

    # Parse 'publishedAt' string to datetime object using defined function
    published_date = parse_published_at(response['items'][0]['snippet']['publishedAt'])

    unsubscribed_trailer_exists = 'brandingSettings' in response['items'][0] and \
                                  'channel' in response['items'][0]['brandingSettings'] and \
                                  'unsubscribedTrailer' in response['items'][0]['brandingSettings']['channel']

    channel_dict = {
        'handle': response['items'][0]['snippet'].get('customUrl', ''),
        'id': response['items'][0]['id'],
        'title': response['items'][0]['snippet']['title'],
        'description': response['items'][0]['snippet']['description'],
        'customUrl': 'https://www.youtube.com/' + response['items'][0]['snippet'].get('customUrl', ''),
        'publishedAt': published_date,
        'viewCount': int(response['items'][0]['statistics']['viewCount']),
        'subscriberCount': int(response['items'][0]['statistics']['subscriberCount']),
        'videoCount': int(response['items'][0]['statistics']['videoCount']),
        'topicIds': response['items'][0]['topicDetails']['topicIds'],
        'topicCategories': response['items'][0]['topicDetails']['topicCategories'],
        'unsubscribedTrailer': unsubscribed_trailer_exists,
        'uploads': response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    }

    return channel_dict

def get_video_data_from_id(youtube, id: str):
    request = youtube.videos().list(
        part='snippet,contentDetails,statistics,localizations',
        id=id,
        maxResults=50
    )
    response = request.execute()

    video_list = []

    for item in response['items']:
        duration = parse_duration(item['contentDetails']['duration'])

        video_dict = {
            'id': item['id'],
            'categoryId': item['snippet']['categoryId'],
            'duration': duration,
            'viewCount': int(item['statistics'].get('viewCount', 0)),
            'likeCount': int(item['statistics'].get('likeCount', 0)),
            'commentCount': int(item['statistics'].get('commentCount', 0))
            }
        video_list.append(video_dict)

    return video_list

def get_activities_data_from_id(youtube, channelId: str):

    activities_items_list = []

    nextPageToken = None

    while True:

        request = youtube.activities().list(
            part='contentDetails,snippet',
            channelId=channelId,
            maxResults=50,
            publishedAfter='2024-02-01T00:00:00.1Z'
        )

        response = request.execute()

        for item in response['items']:

            # Parse 'publishedAt' string to datetime object using defined function
            published_date = parse_published_at(item['snippet']['publishedAt'])

            if item['snippet']['type']=='playlistItem':
                videoId = item['contentDetails']['playlistItem']['resourceId']['videoId']
            else:
                videoId = item['contentDetails']['upload']['videoId']


            activity_dict = {
                'title': item['snippet']['title'],
                'publishedAt': published_date,
                'videoId': videoId,
                'url': 'https://youtu.be/' + videoId,
                'type': item['snippet']['type']
            }

            activities_items_list.append(activity_dict)


        nextPageToken = response.get('nextPageToken')

        if not nextPageToken:
            break

    return activities_items_list


def get_playlist_items_from_id(youtube, id: str):

    playlist_items_list = []

    nextPageToken = None

    while True:

        request = youtube.playlistItems().list(
            part='snippet,contentDetails',
            playlistId=id,
            maxResults=50,
            pageToken=nextPageToken
            )

        response = request.execute()

        # Extract video IDs for the current batch
        video_ids = [item['contentDetails']['videoId'] for item in response['items']]

        # Retrieve video details for the current batch
        video_details = get_video_data_from_id(youtube=youtube, id=','.join(video_ids))

        # Match video details with playlist items and combine information
        for playlist_item in response['items']:
            # Get video ID from playlist item
            video_id = playlist_item['contentDetails']['videoId']

            # Find corresponding video details using video ID
            video_detail = next((detail for detail in video_details if detail['id'] == video_id), None)

            # Parse 'publishedAt' string to datetime object using defined function
            published_date = parse_published_at(playlist_item['contentDetails']['videoPublishedAt'])

            if video_detail:
                pl_item_dict = {
                    'title': playlist_item['snippet']['title'],
                    'description': playlist_item['snippet']['description'],
                    'channelId': playlist_item['snippet']['channelId'],
                    'channelTitle': playlist_item['snippet']['channelTitle'],
                    'videoId': video_id,
                    'url': 'https://youtu.be/' + video_id,
                    'publishedAt': published_date,
                    'categoryId': video_detail['categoryId'],
                    'duration': video_detail['duration'],
                    'viewCount': int(video_detail['viewCount']),
                    'likeCount': int(video_detail['likeCount']),
                    'commentCount': int(video_detail['commentCount'])
                }
            else:
                # Set default values if video details are not available
                pl_item_dict = {
                    'title': playlist_item['snippet']['title'],
                    'description': playlist_item['snippet']['description'],
                    'channelId': playlist_item['snippet']['channelId'],
                    'channelTitle': playlist_item['snippet']['channelTitle'],
                    'videoId': video_id,
                    'url': 'https://youtu.be/' + video_id,
                    'publishedAt': published_date,
                    'categoryId': None,
                    'duration': None,
                    'viewCount': None,
                    'likeCount': None,
                    'commentCount': None
                }

            playlist_items_list.append(pl_item_dict)

        nextPageToken = response.get('nextPageToken')

        if not nextPageToken:
            break

    return playlist_items_list

def get_analytics_data_per_video(youtubeAnalytics, videoId: str, startDate: str, endDate: str):

    report = youtubeAnalytics.reports().query(
    ids="channel==MINE",
    startDate=startDate,
    endDate=endDate,
    metrics="views,likes,shares,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,annotationImpressions,annotationClickThroughRate,annotationCloseRate",
    dimensions="day",
    filters=f"video=={videoId}",
    sort="day"
    ).execute()

    columns = [x['name'] for x in report['columnHeaders']]

    analytics_df = pd.DataFrame(data=report['rows'], columns=columns)

    analytics_df['videoId'] = videoId

    return analytics_df
