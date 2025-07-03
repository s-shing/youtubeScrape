from os import write

from util import Util
import csv

#toggle false means function will not run, true means function will run

# helper function to write video ids to file
def writeToFile(videoIds, file):
    with open(file, "a") as f:
        for videoId in videoIds:
            f.write(videoId + "\n")

# this function gets all videos from channel links
# between 'startdate' and 'enddate'
# argument file should be the title of the file
# with the channel link in it
def getVids(file, **kwargs):
    util = Util()
    startdate = kwargs.get("startdate", None)
    enddate = kwargs.get("enddate", None)
    channelUsers = util.stripUsers(file)
    channelIds = util.getChannelsFromUsers(channelUsers)
    videoIds = util.getVideosFromPlaylist(channelIds,startdate,enddate)
    return videoIds



# returns a list of videos returned by the search query
# filter by maxresults, start date, end date, and
# video return order (date, rating, viewcount) default
# is relevance
def search(query, **kwargs):
    util = Util()

    maxResults = kwargs.get("maxResults", 500)
    startdate = kwargs.get("startdate", None)
    enddate = kwargs.get("enddate", None)
    order = kwargs.get("order", "relevance")
    ret =[]
    vidlist = util.searchQuery(
            query=query,
            maxResults=maxResults,
            startdate=startdate,
            enddate=enddate,
            order=order
        )
    return vidlist


# download all videos from argument file
# all the downloaded videos will be in the 'videos'
# folder download, comments, caption, and
# thumbnail fetch can be toggled
# file input should be csv
def downloadVids(file, **kwargs):
    util = Util()

    with open(file, "r") as f:
        videoIds = csv.reader(f, delimiter="\n")

        toggleDownload = kwargs.get("toggleDownload", False)
        toggleComments = kwargs.get("toggleComments", False)
        toggleCaptions = kwargs.get("toggleCaptions", False)
        toggleThumbnails = kwargs.get("toggleThumbnails", False)
        toggleStatistics = kwargs.get("toggleStatistics", False)

        for videoId in videoIds:
            util.singleVidDownload(videoId, toggleDownload=toggleDownload, toggleComments=toggleComments,
                                   toggleCaptions=toggleCaptions, toggleThumbnails=toggleThumbnails,
                                   toggleStatistics=toggleStatistics)


# download one video by ID, which can be obtained
# from the video url
def downloadVid(videoId, **kwargs):
    util = Util()
    toggleDownload = kwargs.get("toggleDownload", False)
    toggleComments = kwargs.get("toggleComments", False)
    toggleCaptions = kwargs.get("toggleCaptions", False)
    toggleThumbnails = kwargs.get("toggleThumbnails", False)
    toggleStatistics = kwargs.get("toggleStatistics", False)

    util.singleVidDownload(videoId, toggleDownload=toggleDownload, toggleComments=toggleComments, toggleCaptions=toggleCaptions, toggleThumbnails=toggleThumbnails,toggleStatistics=toggleStatistics)


if __name__ == "__main__":
    # vidIDs= getVids("channels.txt",startdate="2024-01-01", enddate="2025-01-01")
    # writeToFile(vidIDs[:10],"channels.csv")
    downloadVids("channels.csv", toggleThumbnails=True,toggleDownload=True,toggleCaptions=True,toggleComments=True,toggleStatistics=True)
