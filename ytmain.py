
from __future__ import unicode_literals
from werkzeug.utils import secure_filename
import json
import os
import re
from datetime import date
import sys


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

def singleVidDownload(videoId, *args, **kwargs):
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    youtube = apiAccess()
    filter = kwargs.get("filter", ["replies", "snippet"])
    toggleDownload = kwargs.get("toggleDownload", True)
    toggleComments = kwargs.get("toggleComments", True)
    toggleCaptions = kwargs.get("toggleCaptions", True)
    toggleThumbnails = kwargs.get("toggleThumbnails", True)

    part = ','.join(filter)
    findtitle = youtube.videos().list(
        part="snippet",
        id=videoId
    )
    info = findtitle.execute()
    if info['items']:
        channel = info["items"][0]["snippet"]["channelTitle"]
    else:
        return
    cleanedchannel = secure_filename(channel)
    cleanedFilename = ("videos/" + cleanedchannel + "/" + str(videoId) + "/Comments - " + str(videoId) + ".txt")
    #ignore download errors and don't overwrite videos
    ydl_opts = {"outtmpl":f"videos/{cleanedchannel}/{str(videoId)}/{str(videoId)}.%(ext)s",
                "ignoreerrors":True, "nooverwrites":True}
    if not toggleDownload:
        ydl_opts["skip_download"] = True
    if toggleCaptions:
        ydl_opts["writesubtitles"] = True
        ydl_opts["writeautomaticsub"] = True
    if toggleThumbnails:
        ydl_opts["writethumbnails"] = True
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download(["https://www.youtube.com/watch?v="+videoId])
    if toggleComments:
        commentRequest = youtube.commentThreads().list(
            part=part,
            videoId=videoId
        )
        try:
            response = commentRequest.execute()
        except googleapiclient.errors.HttpError as err:
            with open(cleanedFilename, "w") as f:
                f.write(err.reason)
        else:
            with open(cleanedFilename, "w") as f:
                f.write(json.dumps(response))


#gets uploads playlist ids
def getChannelsFromUsers(channelNames):
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

#return ids from uploads playlist w/ filter
def getVideosFromPlaylist(channelIds, startdate,enddate):
    youtube = apiAccess()
    ret = []
    i=1
    for channelId in channelIds:
        print(channelId + " - " +str(i)+ "/"+ str(len(channelIds)) )
        ret.append(channelId)
        i+=1
        nextPageToken = ""
        while nextPageToken is not None:
            if nextPageToken == "":
                nextPageToken = None
            request = youtube.playlistItems().list(
                part="contentDetails",
                maxResults=50,
                pageToken=nextPageToken,
                playlistId=channelIds[channelId]
            )
            try:
                response = request.execute()
                #change here to change timeframe
                if not filterVideosByDate(response["items"][0]["contentDetails"]["videoPublishedAt"][:10],startdate=startdate,enddate=None):
                    break
                for item in response['items']:
                    if filterVideosByDate(item["contentDetails"]["videoPublishedAt"][:10],startdate=startdate,enddate=enddate):
                        ret.append(item['contentDetails']['videoId'])
            except TimeoutError as e:
                print(e)
            finally:
                nextPageToken = response.get('nextPageToken')
    return ret

def filterVideosByDate(datePublished,startdate,enddate):

    datePublished = date.fromisoformat(datePublished)
    if startdate is not None and startdate != "":
        startdate = date.fromisoformat(startdate)
        if datePublished <= startdate:
            return False
    if enddate is not None and enddate != "":
        enddate = date.fromisoformat(enddate)
        if datePublished >= enddate:
            return False
    return True

def filterVideosByID(videoId, *args, **kwargs):
    youtube = apiAccess()
    startdate = kwargs.get("startdate", None)
    enddate = kwargs.get("enddate", None)
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
            return False
    if enddate is not None and enddate != "":
        enddate = date.fromisoformat(enddate)
        if datePublished > enddate:
            return False
    return True

def countVideos(filename):
    with open(filename, "r") as f:
        channel =""
        videoCount = 0
        for line in f:
            if len(line)> 20:
                print("channel:",channel)
                print("videocount:",videoCount)
                videoCount = 0
                channel =line
            else:
                videoCount +=1
        print("channel:", channel)
        print("videocount:", videoCount)


if __name__ == "__main__":
    #strips users from a txt list of channels
    channelUsers = stripUsers("channels.txt")
    #get channel ids from users
    channelIds = getChannelsFromUsers(channelUsers)
    #get a list of video IDs from a channel's upload playlist, filtered by date (inclusive)
    videoIds = getVideosFromPlaylist(channelIds,startdate="2024-01-01",enddate="2025-01-01")
    with open("filteredVideos.txt", "a") as f:
        for videoId in videoIds:
            f.write(videoId + "\n")
            #download video and comment with toggle
            singleVidDownload(videoId,toggleDownload=True, toggleComments=True, toggleCaptions=True,toggleThumbnails=True)

