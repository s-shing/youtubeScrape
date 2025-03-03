import re
from datetime import date

from ytmain import apiAccess, stripUsers, multiChannels, getVideosFromPlaylist

#get a channels' video ids, filter, and write to file
if __name__ == "__main__":
    store = []
    channelList = stripUsers("channels.txt")
    channelIds = multiChannels(channelList)
    startdate = "2024-01-01"
    enddate = "2025-01-01"
    videoIds = getVideosFromPlaylist(channelIds,startdate=startdate, enddate=enddate)
    with open("channels-videos-ids1.txt", "w") as f:
        f.write("\n".join(videoIds))