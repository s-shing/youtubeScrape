import re
from datetime import date

from ytmain import apiAccess



#filter videos by channel and date

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
def getVideosFromPlaylist(channelIds):
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
                startdate = "2024-01-01"
                enddate = "2025-01-01"
                if not  filterVideos(response["items"][0]["contentDetails"]["videoPublishedAt"][:10],startdate=startdate,enddate=None):
                    break
                for item in response['items']:
                    if filterVideos(item["contentDetails"]["videoPublishedAt"][:10],startdate=startdate,enddate=enddate):
                        ret.append(item['contentDetails']['videoId'])
            except TimeoutError as e:
                print(e)
            finally:
                nextPageToken = response.get('nextPageToken')
    return ret

def filterVideos(datePublished,startdate,enddate):

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

#get a channels' video ids, filter, and write to file
if __name__ == "__main__":
    store = []
    channelList = stripUsers("channels.txt")
    channelIds = multiChannels(channelList)
    videoIds = getVideosFromPlaylist(channelIds)
    with open("channels-videos-ids.txt", "w") as f:
        f.write("\n".join(videoIds))