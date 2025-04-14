import os
from turtledemo.penrose import start

from matplotlib import pyplot as plt
from werkzeug.utils import secure_filename

import API_Call
import csv
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

def searchQuery(query, maxResults=100, startdate="", enddate=""):
    youtube = apiAccess()
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
            maxResults=50,
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
            i +=50
            nextPageToken = response.get('nextPageToken')
    return ret

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
    if info['items'] and ("statistics") in info['items'][0] and ("snippet") in info['items'][0]:
        ret["viewcount"] = info["items"][0]["statistics"]["viewCount"]
        ret["channelTitle"] = info["items"][0]["snippet"]["channelTitle"]
    else:
        return
    return ret



def mainhelper(query):
    channel_counts = {}
    desired_max_results = 50
    generate_csv = True
    vidlist = searchQuery(
        query=query,
        maxResults=desired_max_results,
        startdate="2024-01-01T00:00:00Z",
        enddate="2025-01-01T00:00:00Z",
    )
    ret ={}
    i=1
    for vid in vidlist:
        print(str(i)+"/"+str(len(vidlist)))
        vidInfo = singleVid(vid, filter=["snippet","statistics"])
        if vidInfo is not None:
            channelname = vidInfo["channelTitle"]
            if ret.get(channelname) is None:
                ret[channelname] = {"viewcount":0, "videocount":0}
                ret[channelname]["viewcount"] += int(vidInfo["viewcount"])
                ret[channelname]["videocount"] += 1
            else:
                ret[channelname]["viewcount"] += int(vidInfo["viewcount"])
                ret[channelname]["videocount"] += 1
        i+=1
    if generate_csv:
        with open("keywords/"+query+".csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Channel", "Video Count", "View Count"])
            for channel in ret:
                writer.writerow([channel, ret[channel]["videocount"], ret[channel]["viewcount"]])

if __name__ == "__main__":
    with open("queries.txt") as f:
        reader = csv.reader(f)
        queries = list(reader)
    for query in queries[0]:
        print(query)
        mainhelper(query)
