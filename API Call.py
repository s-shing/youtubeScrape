from __future__ import unicode_literals

import os
import re
from datetime import date

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


def singleVid(videoId, *args, **kwargs):
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


    cleaned_channel = secure_filename(channel)
    cleaned_title = secure_filename(title)
    video_dir = f"videos/{cleaned_channel}/{cleaned_title}"
    os.makedirs(video_dir, exist_ok=True)

    ydl_opts = {
        "outtmpl": f"{video_dir}/{cleaned_title}.%(ext)s",
        "ignoreerrors": True,
        "nooverwrites": True,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]"
    }
    print(f"Downloading video + audio => {title} (videoId={videoId})")
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"https://www.youtube.com/watch?v={videoId}"])

    metadata_filename = os.path.join(video_dir, f"Metadata - {cleaned_title}.txt")
    with open(metadata_filename, "w", encoding="utf-8") as meta_file:
        meta_file.write(str(info))

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


def searchQuery(query, maxResults=3, startdate="", enddate="", max_duration=None, comment_filter=["replies", "snippet"]):
    youtube = apiAccess()
    req = youtube.search().list(
        part="id,snippet",
        q=query,
        type="video",
        maxResults=maxResults,
    )
    response = req.execute()

    video_ids = []
    for item in response.get("items", []):
        video_id = item["id"]["videoId"]
        video_ids.append(video_id)

    for vid in video_ids:
        singleVid(
            vid,
            filter=comment_filter,
            startdate=startdate,
            enddate=enddate,
            max_duration=max_duration 
        )


if __name__ == "__main__":
    searchQuery(
        query="Ghana election",
        maxResults=5,                  
        startdate="",                  
        enddate="",
        max_duration=30,                    
        comment_filter=["replies", "snippet"]
    )

