from __future__ import unicode_literals
import json
import re
from datetime import date
import os

from werkzeug.utils import secure_filename


import googleapiclient.discovery
import googleapiclient.errors

import yt_dlp as youtube_dl
import googleapiclient.discovery
import googleapiclient.errors



# this class contains all the necessary functions
# for processing. create a util object and call the
# functions within
scopes = ["https://www.googleapis.com/auth/youtube.readonly"]


class Util:
    def __init__(self):
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        # client_secrets_file = "YOUR_CLIENT_SECRET_FILE.json"
        DEVELOPER_KEY = os.environ["YT_API_KEY"]

        # Get credentials and create an API client

        youtube = googleapiclient.discovery.build(
            api_service_name, api_version, developerKey=DEVELOPER_KEY)
        self.request = youtube

    def searchQuery(self, query, **kwargs):
        youtube = self.request
        maxResults = kwargs.get("maxResults", 500)
        startdate = kwargs.get("startdate", None)
        enddate = kwargs.get("enddate", None)
        ret = []
        i = 0
        nextPageToken = ""
        while nextPageToken is not None and i <= maxResults:
            if nextPageToken == "":
                nextPageToken = None
            request = youtube.search().list(
                part="id,snippet",
                q=query,
                type="video",
                maxResults=maxResults,
                pageToken=nextPageToken,
                publishedBefore=enddate,
                publishedAfter=startdate
            )

            try:
                response = request.execute()
                for item in response['items']:
                    ret.append(item["id"]["videoId"])
            except TimeoutError as e:
                print(e)
            finally:
                i += 50
                if response is None:
                    nextPageToken = response.get('nextPageToken')
                else:
                    nextPageToken = None
        return ret

    def singleVidDownload(self, videoId,*args, **kwargs):
        youtube = self.request
        videoId  = videoId[0]
        toggleDownload = kwargs.get("toggleDownload", False)
        toggleComments = kwargs.get("toggleComments", False)
        toggleCaptions = kwargs.get("toggleCaptions", False)
        toggleThumbnails = kwargs.get("toggleThumbnails", False)
        toggleStatistics = kwargs.get("toggleStatistics", False)
        findtitle = youtube.videos().list(
            part=["snippet","statistics"],
            id=videoId
        )
        info = findtitle.execute()
        if info['items']:
            channel = info["items"][0]["snippet"]["channelTitle"]
        else:
            return
        cleanedchannel = secure_filename(channel)
        cleanedFilename = ("videos/" + cleanedchannel + "/" + str(videoId) + "/Comments - " + str(videoId) + ".txt")
        # ignore download errors and don't overwrite videos
        ydl_opts = {"outtmpl": f"videos/{cleanedchannel}/{str(videoId)}/{str(videoId)}.%(ext)s",
                    "ignoreerrors": True, "nooverwrites": True,}
        if not toggleDownload:
            ydl_opts["skip_download"] = True

        if toggleCaptions:
            #having caption issue with ytdl api, may have to rewrite for inline
            pass
        if toggleThumbnails:
            ydl_opts["writethumbnail"] = True
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download(["https://www.youtube.com/watch?v=" + videoId])
        if toggleComments:
            commentRequest = youtube.commentThreads().list(
                part=["snippet","replies"],
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
        if toggleStatistics:
            cleanedFilenameStats = (
                        "videos/" + cleanedchannel + "/" + str(videoId) + "/Statistics - " + str(videoId) + ".txt")
            with open(cleanedFilenameStats, 'w') as f:
                f.write(json.dumps(info['items'][0]['statistics']))

    # gets uploads playlist ids
    def getChannelsFromUsers(self, channelNames):
        youtube = self.request
        ret = {}
        for channelName in channelNames:
            request = youtube.channels().list(
                part="id, contentDetails",
                forHandle=channelName
            )
            response = request.execute()
            ret[response['items'][0]["id"]] = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        return ret

    def stripUsers(self, filename):
        with open(filename, "r") as f:
            names = []
            for line in f:
                if "https://www.youtube.com/" in line:
                    padding = len("https://www.youtube.com/@")
                    start = line.index("https://www.youtube.com/@") + padding
                    end = re.search("\\s|/+", line[start:]).end() + padding - 1
                    names.append(line[start:end])
            return names

    # return ids from uploads playlist w/ filter
    def getVideosFromPlaylist(self, channelIds, startdate, enddate):
        youtube = self.request
        ret = []
        i = 1
        for channelId in channelIds:
            print(channelId + " - " + str(i) + "/" + str(len(channelIds)))
            ret.append(channelId)
            i += 1
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
                    # change here to change timeframe
                    if not self.filterVideosByDate(response["items"][0]["contentDetails"]["videoPublishedAt"][:10],
                                                   startdate=startdate, enddate=None):
                        break
                    for item in response['items']:
                        if self.filterVideosByDate(item["contentDetails"]["videoPublishedAt"][:10], startdate=startdate,
                                                   enddate=enddate):
                            ret.append(item['contentDetails']['videoId'])
                except TimeoutError as e:
                    print(e)
                finally:
                    nextPageToken = response.get('nextPageToken')
        return ret

    def filterVideosByDate(self, datePublished, startdate, enddate):
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

    def filterVideosByID(self, videoId, *args, **kwargs):
        youtube = self.request
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

    def countVideos(self, filename):
        with open(filename, "r") as f:
            channel = ""
            videoCount = 0
            for line in f:
                if len(line) > 20:
                    print("channel:", channel)
                    print("videocount:", videoCount)
                    videoCount = 0
                    channel = line
                else:
                    videoCount += 1
            print("channel:", channel)
            print("videocount:", videoCount)
