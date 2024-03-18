# youtube_api.py

from googleapiclient.discovery import build
from datetime import datetime, timedelta
import re
import pandas as pd

def parse_published_at(published_at_str):
    """
    Parses the 'publishedAt' string into a datetime.date object.

    The function attempts to parse the input string with multiple formats, 
    including milliseconds, without milliseconds, and with timezone offset.
    If parsing fails for all formats, it raises a ValueError.

    Args:
        published_at_str (str): A string representing the publishedAt timestamp.

    Returns:
        datetime.date: The date extracted from the parsed timestamp.

    Raises:
        ValueError: If the input string does not match any of the expected formats.
    """
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
    """
    Parse a YouTube video duration string into total duration in seconds.

    Args:
        duration_str (str): A string representing the duration of a YouTube video.

    Returns:
        int: Total duration of the video in seconds.

    """

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


def extract_hashtags(description):
    """
    Extract hashtags from a given description.

    Args:
        description (str): The description from which hashtags will be extracted.

    Returns:
        list: A list of hashtags found in the description.

    """
    hashtags = re.findall(r'#\w+', description)
    return hashtags

def get_channel_data_from_handle(api_client, handle: str):
    """
    Retrieve data about a YouTube channel using the handle.

    Args:
        api_client: An initialized instance of the YouTube API client.
        handle (str): The handle (username) of the YouTube channel.

    Returns:
        dict: A dictionary containing data about the YouTube channel.

    """
    request = api_client.channels().list(
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

def get_video_data_from_id(api_client, id: str):
    """
    Retrieve data about a YouTube video using its ID.

    Args:
        api_client: An initialized instance of the YouTube API client.
        id (str): The ID of the YouTube video.

    Returns:
        list: A list of dictionaries containing data about the YouTube videos.

    """
    request = api_client.videos().list(
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

def get_activities_data_from_id(api_client, channelId: str):
    """
    Retrieve activities data for a YouTube channel using its channel ID.

    Args:
        api_client: An initialized instance of the YouTube API client.
        channelId (str): The channel ID of the YouTube channel.

    Returns:
        list: A list of dictionaries containing activities data for the channel.

    """
    activities_items_list = []

    nextPageToken = None

    while True:

        request = api_client.activities().list(
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


def get_playlist_items_from_id(api_client, id: str):
    """
    Retrieve playlist items data for a YouTube playlist using its playlist ID.

    This function fetches information about the videos in the specified playlist,
    including details such as title, description, channel ID, channel title, video ID,
    URL, published date, category ID, duration, view count, like count, and comment count.

    Args:
        api_client: An initialized instance of the YouTube API client.
        id (str): The playlist ID of the YouTube playlist.

    Returns:
        list: A list of dictionaries containing playlist items data.
              Each dictionary represents a playlist item and contains the following keys:
              - title: Title of the playlist item.
              - description: Description of the playlist item.
              - channelId: Channel ID of the playlist item.
              - channelTitle: Channel title of the playlist item.
              - videoId: Video ID of the playlist item.
              - url: URL of the playlist item.
              - publishedAt: Published date of the playlist item.
              - categoryId: Category ID of the playlist item.
              - duration: Duration of the playlist item (in seconds).
              - viewCount: View count of the playlist item.
              - likeCount: Like count of the playlist item.
              - commentCount: Comment count of the playlist item.

    """
    playlist_items_list = []

    nextPageToken = None

    while True:

        request = api_client.playlistItems().list(
            part='snippet,contentDetails',
            playlistId=id,
            maxResults=50,
            pageToken=nextPageToken
            )

        response = request.execute()

        # Extract video IDs for the current batch
        video_ids = [item['contentDetails']['videoId'] for item in response['items']]

        # Retrieve video details for the current batch
        video_details = get_video_data_from_id(api_client, id=','.join(video_ids))

        # Match video details with playlist items and combine information
        for playlist_item in response['items']:
            # Get video ID from playlist item
            video_id = playlist_item['contentDetails']['videoId']

            # Find corresponding video details using video ID
            video_detail = next((detail for detail in video_details if detail['id'] == video_id), None)

            # Parse 'publishedAt' string to datetime object using defined function
            published_date = parse_published_at(playlist_item['contentDetails']['videoPublishedAt'])

            #write the dictionary for the individual video
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

def get_analytics_data_per_video(api_client, videoId: str, startDate: str, endDate: str):
    """
    Retrieve analytics data for a specific video within a specified date range.

    This function queries the YouTube Analytics API to fetch various metrics and dimensions
    for a particular video over a specified time period. The metrics include views, likes, shares,
    estimated minutes watched, average view duration, average view percentage, annotation impressions,
    annotation click-through rate, and annotation close rate.

    Args:
        api_client: An initialized instance of the YouTube Analytics API client.
        videoId (str): The ID of the YouTube video for which analytics data is to be retrieved.
        startDate (str): The start date of the date range in the format 'YYYY-MM-DD'.
        endDate (str): The end date of the date range in the format 'YYYY-MM-DD'.

    Returns:
        pandas.DataFrame: A DataFrame containing the analytics data for the specified video.
                          Each row represents a day within the specified date range, and the columns
                          include metrics such as views, likes, shares, etc. Additionally, the DataFrame
                          contains a 'videoId' column with the ID of the corresponding video.

    """
    report = api_client.reports().query(
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
