import json

import googleapiclient
from werkzeug.utils import secure_filename

import ytmain

#calculate average comments from videos

def getComments(videoId, *args, **kwargs):
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    youtube = ytmain.apiAccess()
    filter = kwargs.get("filter", ["replies", "snippet"])
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
    if info['items']:
        channel = info["items"][0]["snippet"]["channelTitle"]
        title = info["items"][0]["snippet"]["title"]
    cleanedchannel = secure_filename(channel)
    cleanedtitle = secure_filename(title)
    cleanedFilename = ("videos/Comments - " + cleanedtitle + ".txt")
    try:
        response = request.execute()
    except googleapiclient.errors.HttpError as err:
        return None
    else:
        return response

if __name__ == "__main__":
    with open("channels-videos.txt", "r") as f:
        linenum=0
        commentnum = 0
        for line in f:
            response = getComments(line.replace("\n",""))
            if response is not None and response.get("items") is not None:
                commentnum += len(response.get("items"))
            linenum+=1
            print("line:", linenum)
            print("comments:", commentnum)
        print("total comments =" +str(commentnum))
        print("total videos =" +str(linenum))
        print("average comments =" +str(commentnum/linenum))