import os
from turtledemo.penrose import start

from matplotlib import pyplot as plt
from werkzeug.utils import secure_filename

import API_Call
import csv

import search
import ytmain
import yt_dlp as youtube_dl
import googleapiclient.discovery
import googleapiclient.errors

from API_Call import singleVid

scopes = ["https://www.googleapis.com/auth/youtube.readonly"]

def apiAccess():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"
    # client_secrets_file = "YOUR_CLIENT_SECRET_FILE.json"
    DEVELOPER_KEY = os.environ["YT_API_KEY"]

    # Get credentials and create an API client

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, developerKey=DEVELOPER_KEY)
    return youtube


def singleVid(videoId, *args, **kwargs):
    if videoId is None:
        return
    ret ={}
    youtube = apiAccess()
    filter = kwargs.get("filter", ["snippet"])
    part = ','.join(filter)

    findtitle = youtube.videos().list(
        part=part,
        id=videoId
    )
    info = findtitle.execute()
    if info['items'] and ("snippet") in info['items'][0]:
        ret["tag"] = info["items"][0]["snippet"]["tags"]
        ret["channelTitle"] = info["items"][0]["snippet"]["channelTitle"]
    else:
        return
    return ret



def mainhelper(query):
    channel_counts = {}
    desired_max_results = 50
    generate_csv = True
    vidlist = search.searchQuery(
        query=query,
        maxResults=desired_max_results,
        startdate="2024-01-01T00:00:00Z",
        enddate="2025-01-01T00:00:00Z",
    )
    ret ={}
    i=1
    for vid in vidlist:
        print(str(i)+"/"+str(len(vidlist)))
        vidInfo = singleVid(vid, filter=["snippet","tags"])
        if vidInfo is not None:
            channelname = vidInfo["channelTitle"]
            if ret.get(channelname) is None:
                ret[channelname] = []
                ret[channelname].append(vidInfo["tag"])
            else:
                ret[channelname].append(vidInfo["tag"])
        i+=1
    if generate_csv:
        with open("tags/"+query+".csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Channel", "Tag"])
            for channel in ret:
                writer.writerow([channel, ret[channel] ])

if __name__ == "__main__":
    mainhelper("US election")
