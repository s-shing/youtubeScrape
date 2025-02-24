from __future__ import unicode_literals

import os
import re
from datetime import date
import matplotlib.pyplot as plt
from werkzeug.utils import secure_filename
from isodate import parse_duration
import yt_dlp as youtube_dl

import googleapiclient.discovery
import googleapiclient.errors

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    CouldNotRetrieveTranscript
)

def apiAccess():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"

    DEVELOPER_KEY = ""

    youtube = googleapiclient.discovery.build(
        api_service_name,
        api_version,
        developerKey=DEVELOPER_KEY
    )
    return youtube


def singleVid(videoId, *args, download_video, download_comments, download_transcript, channel_counts=None, **kwargs):
    youtube = apiAccess()

    startdate = kwargs.get("startdate", None)
    enddate = kwargs.get("enddate", None)
    comment_filter = kwargs.get("filter", ["replies", "snippet"])
    part = ",".join(comment_filter)

    request_meta = youtube.videos().list(
        part="snippet,contentDetails",
        id=videoId
    )
    info = request_meta.execute()

    if not info["items"]:
        return

    item = info["items"][0]
    snippet = item["snippet"]
    content_details = item["contentDetails"]
    channel = snippet["channelTitle"]
    title = snippet["title"]
    publish_date_str = snippet["publishedAt"][:10]
    publish_date = date.fromisoformat(publish_date_str)

    if startdate:
        start_dt = date.fromisoformat(startdate)
        if publish_date < start_dt:
            return
    if enddate:
        end_dt = date.fromisoformat(enddate)
        if publish_date > end_dt:
            return
    
    duration_iso = content_details["duration"]
    duration_td = parse_duration(duration_iso)
    duration_in_minutes = duration_td.total_seconds() / 60.0

    max_duration = kwargs.get("max_duration", None)
    if max_duration is not None:
        if duration_in_minutes > max_duration:
            print(
                f"Skipping video {videoId} because it's longer "
                f"than {max_duration} min (actual: ~{int(duration_in_minutes)} min)."
            )
            return

    if channel_counts is not None:
        channel_counts[channel] = channel_counts.get(channel, 0) + 1

    cleaned_channel = secure_filename(channel)
    cleaned_title = secure_filename(title)
    video_dir = f"videos/{cleaned_channel}/{cleaned_title}"
    os.makedirs(video_dir, exist_ok=True)
    
    metadata_filename = os.path.join(video_dir, f"Metadata - {cleaned_title}.txt")
    with open(metadata_filename, "w", encoding="utf-8") as meta_file:
        meta_file.write(str(info))

    if download_video:
        ydl_opts = {
            "outtmpl": f"{video_dir}/{cleaned_title}.%(ext)s",
            "ignoreerrors": True,
            "nooverwrites": True,
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]"
        }
        print(f"Downloading video + audio => {title} (videoId={videoId})")
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={videoId}"])

    if download_comments:
        comments_filename = os.path.join(video_dir, f"Comments - {cleaned_title}.txt")
        request_comments = youtube.commentThreads().list(
            part=part,
            videoId=videoId
        )
        try:
            comments_response = request_comments.execute()
        except googleapiclient.errors.HttpError as err:
            with open(comments_filename, "w", encoding="utf-8") as cfile:
                cfile.write(f"Error retrieving comments: {str(err)}")
        else:
            with open(comments_filename, "w", encoding="utf-8") as cfile:
                cfile.write(str(comments_response))

    if download_transcript:
        transcript_filename = os.path.join(video_dir, f"Transcript - {cleaned_title}.txt")
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(videoId, languages=['en', 'en-US'])
        except (TranscriptsDisabled, NoTranscriptFound, CouldNotRetrieveTranscript) as e:
            print(f"No transcript found for video: {videoId} ({str(e)})")
            return
        except Exception as e:
            return
        else:
            with open(transcript_filename, "w", encoding="utf-8") as tfile:
                tfile.write(str(transcript_list))

def stripUsers(filename):
    with open(filename, "r", encoding="utf-8") as f:
        names = []
        for line in f:
            if "https://www.youtube.com/" in line:
                padding = len("https://www.youtube.com/@")
                start = line.index("https://www.youtube.com/@") + padding
                match = re.search(r"\s|/+", line[start:])
                if match:
                    end = start + match.start()
                else:
                    end = len(line)
                names.append(line[start:end].strip())
        return names

def plotChannelCounts(channel_counts, top_n=20):
    sorted_items = sorted(channel_counts.items(), key=lambda x: x[1], reverse=True)
    if not sorted_items:
        print("No data to plot.")
        return
    
    top_channels = sorted_items[:top_n]
    remainder = sorted_items[top_n:]
    
    if remainder:
        others_count = sum(x[1] for x in remainder)
        top_channels.append(("Others", others_count))

    channels, counts = zip(*sorted_items)
    
    plt.figure(figsize=(12, 6))
    plt.bar(channels, counts, color='steelblue')
    plt.title("Number of Retrieved Videos per Channel")
    plt.xlabel("Channel")
    plt.ylabel("Video Count")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.show()

def multiChannels(channelNames):
    youtube = apiAccess()
    ret = {}
    for channelName in channelNames:
        req = youtube.channels().list(part="id, contentDetails", forHandle=channelName)
        response = req.execute()
        if response['items']:
            channel_id = response['items'][0]["id"]
            uploads_playlist = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            ret[channel_id] = uploads_playlist
    return ret


def getVideosFromPlaylist(channelIds, vidNumber):
    youtube = apiAccess()
    ret = []
    for ch_id, pl_id in channelIds.items():
        req = youtube.playlistItems().list(
            part="contentDetails",
            maxResults=vidNumber,
            playlistId=pl_id
        )
        response = req.execute()
        for item in response.get('items', []):
            ret.append(item['contentDetails']['videoId'])
    return ret


def searchQuery(query, maxResults=500, startdate="", enddate="", max_duration=None, comment_filter=["replies", "snippet"], download_video=True, download_comments=True, download_transcript=True, channel_counts=None):
    youtube = apiAccess()
    
    all_video_ids = set()
    next_page_token = None
    previous_page_token = None
    results_per_page = 50
    
    while len(all_video_ids) < maxResults:
        req = youtube.search().list(
            part="id,snippet",
            q=query,
            type="video",
            maxResults=maxResults,
            pageToken=next_page_token
        )
        response = req.execute()
        
        
        items = response.get("items", [])
        before_count = len(all_video_ids)
        for item in items:
            video_id = item["id"]["videoId"]
            all_video_ids.add(video_id)
        after_count = len(all_video_ids)
        new_ids_count = after_count - before_count
        if new_ids_count == 0:
            print("No new video IDs found on this page. Breaking.")
            break

        previous_page_token = next_page_token
        next_page_token = response.get("nextPageToken")
        print("Next page token:", next_page_token)
        if not next_page_token or next_page_token == previous_page_token:
            break
    
    
    for vid in all_video_ids:
        singleVid(
            vid,
            filter=comment_filter,
            startdate=startdate,
            enddate=enddate,
            max_duration=max_duration,
            download_video=download_video,
            download_comments=download_comments,
            download_transcript=download_transcript,
            channel_counts=channel_counts
        )


if __name__ == "__main__":
    channel_counts = {}
    searchQuery(
        query="Ghana election",
        maxResults=500,                  
        startdate="",                  
        enddate="",
        max_duration=None,                    
        comment_filter=["replies", "snippet"],
        download_video=False,
        download_comments=False,
        download_transcript=False,
        channel_counts=channel_counts 
    )
    plotChannelCounts(channel_counts)

