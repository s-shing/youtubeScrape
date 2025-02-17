# -*- coding: utf-8 -*-

# Sample Python code for youtube.channels.txt.list
# See instructions for running these code samples locally:
# https://developers.google.com/explorer-help/code-samples#python
from __future__ import unicode_literals
from werkzeug.utils import secure_filename
import json
import os
import re
from datetime import date
import ffmpeg

import yt_dlp as youtube_dl
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

def singleVid(videoId, *args, **kwargs):
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    youtube = apiAccess()
    startdate = kwargs.get("startdate", None)
    enddate = kwargs.get("enddate", None)
    filter =  kwargs.get("filter", ["replies","snippet"])
    part = ','.join(filter)
    request = youtube.commentThreads().list(
        part=part,
        videoId=videoId
    )
    findtitle = youtube.videos().list(
        part="snippet",
        id=videoId
    )
    info = findtitle.execute()
    datePublished = info["items"][0]["snippet"]["publishedAt"][:10]
    datePublished = date.fromisoformat(datePublished)
    if startdate is not None and startdate != "":
        startdate = date.fromisoformat(startdate)
        if datePublished < startdate:
            return
    if enddate is not None and enddate != "":
        enddate = date.fromisoformat(enddate)
        if datePublished > enddate:
            return
    if info['items']:
        channel = info["items"][0]["snippet"]["channelTitle"]
        title = info["items"][0]["snippet"]["title"]
    cleanedchannel = secure_filename(channel)
    cleanedtitle = secure_filename(title)
    cleanedFilename = ("videos/" + cleanedchannel + "/" + cleanedtitle + "/Comments - " + cleanedtitle + ".txt")
    #ignore download errors and don't overwrite videos
    ydl_opts = {"outtmpl":f"videos/{cleanedchannel}/{cleanedtitle}/{cleanedtitle}.%(ext)s",
                "ignoreerrors":True, "nooverwrites":True}

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download(["https://www.youtube.com/watch?v="+videoId])
    try:
        response = request.execute()
    except googleapiclient.errors.HttpError as err:
        with open(cleanedFilename, "w") as f:
            f.write(err.reason)
    else:
        with open(cleanedFilename, "w") as f:
            f.write(json.dumps(response))

def multiChannels(channelNames):
    youtube = apiAccess()
    ret = {}
    for channelName in channelNames:
        request = youtube.channels().list(
            part="id, contentDetails",
            forHandle=channelName
        )
        response = request.execute()
        ret[response['items'][0]["id"]] = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    return ret

def stripUsers(filename):
    with open(filename, "r") as f:
        names =[]
        for line in f:
            if "https://www.youtube.com/" in line:
                padding = len("https://www.youtube.com/@")
                start = line.index("https://www.youtube.com/@") + padding
                end = re.search("\\s|/+",line[start:]).end()+padding-1
                names.append(line[start:end])
        return names

#return ids from uploads playlist
def getVideosFromPlaylist(channelIds,vidNumber):
    youtube = apiAccess()
    ret = []
    for channelId in channelIds:
        request = youtube.playlistItems().list(
            part="contentDetails",
            #maxresults dictates how many videos from the playlist
            maxResults=vidNumber,
            playlistId=channelIds[channelId]
        )
        response = request.execute()
        for item in response['items']:
            ret.append(item['contentDetails']['videoId'])
    return ret

if __name__ == "__main__":
    #strips channel usernames from links in channels.txt.txt
    channelList = stripUsers("test.txt")
    #grabs channel ids from usernames
    channelIds = multiChannels(channelList)
    #gets all uploaded video id's from channel ID, vidNumber = number of uploads to grab
    videoIds = getVideosFromPlaylist(channelIds,6)
    for video in videoIds:
        #singlevid filter should be in the format of a list ex ["replies","snippet"]
        #start/end time should be in the format year-mm-dd, undeclared, or empty string ""
        #singlevid downloads video + comments, returns nothing if not between start and end
        singleVid(video, filter=["replies","snippet"], startdate="", enddate="")
