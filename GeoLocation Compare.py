from __future__ import unicode_literals
import csv
import os
import re
from datetime import date
import matplotlib.pyplot as plt
from werkzeug.utils import secure_filename
from isodate import parse_duration
import yt_dlp as youtube_dl
import numpy as np

import googleapiclient.discovery
import googleapiclient.errors

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    CouldNotRetrieveTranscript
)

def apiAccess():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    api_service_name = "youtube"
    api_version = "v3"
    DEVELOPER_KEY = ""
    youtube = googleapiclient.discovery.build(
        api_service_name,
        api_version,
        developerKey=DEVELOPER_KEY
    )
    return youtube

def getChannelCountry(channel_id, youtube, channel_country_cache):
    if channel_id in channel_country_cache:
        return channel_country_cache[channel_id]
    req = youtube.channels().list(part="snippet", id=channel_id)
    resp = req.execute()
    if resp.get("items"):
        s = resp["items"][0]["snippet"]
        c = s.get("country", "Unknown")
        channel_country_cache[channel_id] = c
    else:
        channel_country_cache[channel_id] = "Unknown"
    return channel_country_cache[channel_id]

def singleVid(
    videoId,
    *args,
    channel_counts=None,
    country_counts=None,
    channel_country_cache=None,
    **kwargs
):
    youtube = apiAccess()
    startdate = kwargs.get("startdate", None)
    enddate = kwargs.get("enddate", None)
    comment_filter = kwargs.get("filter", ["replies", "snippet"])
    part = ",".join(comment_filter)
    request_meta = youtube.videos().list(part="snippet,contentDetails", id=videoId)
    info = request_meta.execute()
    if not info["items"]:
        return
    item = info["items"][0]
    snippet = item["snippet"]
    channel = snippet["channelTitle"]
    channel_id = snippet["channelId"]
    publish_date_str = snippet["publishedAt"][:10]
    publish_date = date.fromisoformat(publish_date_str)
    if startdate:
        start_dt = date.fromisoformat(startdate)
        if publish_date < start_dt:
            return
    if enddate:
        end_dt = date.fromisoformat(enddate)
        if publish_date > end_dt:
            return
    if channel_counts is not None:
        channel_counts[channel] = channel_counts.get(channel, 0) + 1
    if country_counts is not None and channel_country_cache is not None:
        channel_country = getChannelCountry(channel_id, youtube, channel_country_cache)
        country_counts[channel_country] = country_counts.get(channel_country, 0) + 1

def plotCountryCounts(country_counts, top_n):
    sorted_items = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
    if not sorted_items:
        return
    top_countries = sorted_items[:top_n]
    remainder = sorted_items[top_n:]
    if remainder:
        others_count = sum(x[1] for x in remainder)
        top_countries.append(("Others", others_count))
    countries, counts = zip(*top_countries)
    plt.figure(figsize=(12, 6))
    bars = plt.bar(countries, counts)
    for bar in bars:
        height = bar.get_height()
        plt.annotate(
            str(height),
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha='center',
            va='bottom'
        )
    plt.title(f"Number of Retrieved Videos per Country (Top {top_n})")
    plt.xlabel("Country")
    plt.ylabel("Video Count")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.show()
    return sorted_items

def plotMultiRegionCountryCounts(region_country_counts, top_n):
    all_countries = set()
    for rc in region_country_counts:
        all_countries.update(region_country_counts[rc].keys())
    totals = {}
    for c in all_countries:
        s = 0
        for rc in region_country_counts:
            s += region_country_counts[rc].get(c, 0)
        totals[c] = s
    sorted_countries = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_countries) > top_n:
        top_countries = [x[0] for x in sorted_countries[:top_n]]
    else:
        top_countries = [x[0] for x in sorted_countries]
    region_list = list(region_country_counts.keys())
    region_list.sort()
    x = np.arange(len(top_countries))
    bar_width = 0.8 / len(region_list)
    plt.figure(figsize=(12, 6))
    for i, rc in enumerate(region_list):
        y = [region_country_counts[rc].get(c, 0) for c in top_countries]
        plt.bar(x + i * bar_width, y, bar_width, label=rc)
        for idx, val in enumerate(y):
            if val > 0:
                plt.annotate(
                    str(val),
                    xy=(x[idx] + i*bar_width, val),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center',
                    va='bottom'
                )
    plt.xticks(x + bar_width*(len(region_list)-1)/2, top_countries, rotation=45, ha="right")
    plt.xlabel("Country")
    plt.ylabel("Video Count")
    plt.title(f"Comparison of Video Counts by Country Across Regions (Top {top_n})")
    plt.legend(title="Region")
    plt.tight_layout()
    plt.show()

def searchQuery(
    query,
    maxResults=500,
    startdate="",
    enddate="",
    channel_counts=None,
    country_counts=None,
    region_code=""
):
    youtube = apiAccess()
    all_video_ids = set()
    next_page_token = None
    previous_page_token = None
    results_per_page = 50
    channel_country_cache = {}
    while len(all_video_ids) < maxResults:
        req = youtube.search().list(
            part="id,snippet",
            q=query,
            type="video",
            maxResults=results_per_page,
            pageToken=next_page_token,
            regionCode=region_code
        )
        response = req.execute()
        items = response.get("items", [])
        before_count = len(all_video_ids)
        for item in items:
            video_id = item["id"]["videoId"]
            all_video_ids.add(video_id)

        after_count = len(all_video_ids)
        new_ids_count = after_count - before_count
        if new_ids_count == 0:
            break
        previous_page_token = next_page_token
        next_page_token = response.get("nextPageToken")
        if not next_page_token or next_page_token == previous_page_token:
            break
    for vid in all_video_ids:
        singleVid(
            vid,
            startdate=startdate,
            enddate=enddate,
            channel_counts=channel_counts,
            country_counts=country_counts,
            channel_country_cache=channel_country_cache
        )
    return all_video_ids

if __name__ == "__main__":
    regions = ["US", "AU", "GB", "IN"]
    query = "Trump Rally Madison Square Garden"
    start_date = "2024-06-01"
    end_date = "2024-12-31"
    max_results = 120
    region_country_counts = {}
    for rc in regions:
        cc = {}
        searchQuery(
            query=query,
            maxResults=max_results,
            startdate=start_date,
            enddate=end_date,
            country_counts=cc,
            region_code=rc
        )
        region_country_counts[rc] = cc
    plotMultiRegionCountryCounts(region_country_counts, top_n=20)
