# -*- coding: utf-8 -*-

# Sample Python code for youtube.channels.list
# See instructions for running these code samples locally:
# https://developers.google.com/explorer-help/code-samples#python
from __future__ import unicode_literals

import json
import os
import yt_dlp as youtube_dl
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

scopes = ["https://www.googleapis.com/auth/youtube.readonly"]

def apiAccess():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"
    # client_secrets_file = "YOUR_CLIENT_SECRET_FILE.json"
    DEVELOPER_KEY = ""

    # Get credentials and create an API client

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, developerKey=DEVELOPER_KEY)
    return youtube

def singleVid(videoId, filter):
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    youtube = apiAccess()
    part = ','.join(filter)
    request = youtube.commentThreads().list(
        part=part,
        videoId=videoId
    )
    findtitle = youtube.videos().list(
        part="snippet",
        id=videoId
    )
    title = findtitle.execute()
    title = title["items"][0]["snippet"]["title"]

    response = request.execute()
    ydl_opts = {"outtmpl":"videos/%(title)s/%(title)s.%(ext)s"}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download(["https://www.youtube.com/watch?v="+videoId])
    with open("videos/"+title+"/Comments - "+title+".txt", "w") as f:
        f.write(json.dumps(response))

if __name__ == "__main__":
    singleVid("dQw4w9WgXcQ",["replies","snippet"])