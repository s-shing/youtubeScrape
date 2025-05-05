import csv, sys, collections
import numpy as np
import matplotlib.pyplot as plt
import squarify
from googleapiclient.discovery import build

API_KEY   = ""
QUERY     = "Ghana Elections 2024"
MAX_RESULTS = 750
CSV_OUT      = "youtube_metadata.csv"
SUMMARY_CSV  = "run_stats.csv"
TREEMAP_MAX_BOXES = 60
BAR_TOP_N        = 30


def yt_service(key):
    return build("youtube", "v3", developerKey=key, cache_discovery=False)


def search_top_ids(ytsvc, q, k):
    ids, token = [], None
    while len(ids) < k:
        batch = min(50, k - len(ids))
        resp = ytsvc.search().list(
            q=q, part="id", type="video", order="viewCount",
            maxResults=batch, pageToken=token or ""
        ).execute()
        ids += [it["id"]["videoId"] for it in resp.get("items", [])
                if it["id"].get("videoId")]
        token = resp.get("nextPageToken")
        if not token:
            break
    return ids[:k]


def fetch_metadata(ytsvc, vid_ids):
    rows = []
    for i in range(0, len(vid_ids), 50):
        batch = ",".join(vid_ids[i:i+50])
        resp = ytsvc.videos().list(part="snippet,statistics", id=batch).execute()
        for it in resp.get("items", []):
            snip, stats = it["snippet"], it["statistics"]
            rows.append({
                "video_id": it["id"],
                "title": snip.get("title", ""),
                "published": snip.get("publishedAt", ""),
                "views": int(stats.get("viewCount", 0)),
                "tags": snip.get("tags", []) or []
            })
    return sorted(rows, key=lambda r: r["views"], reverse=True)


def save_metadata(rows, path):
    with open(path, "w", newline='', encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["video_id", "title", "published", "views", "tags"])
        for r in rows:
            w.writerow([r["video_id"], r["title"], r["published"],
                        r["views"], "|".join(r["tags"])])
    print(f"✓ CSV written: {path}")


def append_run_summary(query, s, path):
    first = not (path and os.path.exists(path))
    with open(path, "a", newline='', encoding="utf-8") as f:
        w = csv.writer(f)
        if first:
            w.writerow(["query", "total", "with_tag", "no_tag",
                        "pct_with_tag", "pct_no_tag", "one_to_five", "gt5"])
        w.writerow([query, s["total"], s["with_tag"], s["no_tag"],
                    f"{s['pct_with_tag']:.1f}", f"{s['pct_no_tag']:.1f}",
                    s["le5"], s["gt5"]])
    print(f"✓ Summary appended to {path}")


def tag_stats(rows):
    tot = len(rows)
    no_tag = sum(1 for r in rows if not r["tags"])
    gt5    = sum(1 for r in rows if len(r["tags"]) > 5)
    le5    = tot - no_tag - gt5
    return {
        "total": tot,
        "with_tag": tot - no_tag,
        "pct_with_tag": (tot - no_tag)/tot*100,
        "no_tag": no_tag,
        "pct_no_tag": no_tag/tot*100,
        "gt5": gt5,
        "pct_gt5": gt5/tot*100,
        "le5": le5,
        "pct_le5": le5/tot*100
    }


def tag_frequency(rows):
    freq = collections.Counter()
    for r in rows:
        freq.update([t.lower().strip() for t in r["tags"]])
    return freq


def plot_treemap(freq):
    labels = [f"{t}\n({c})" for t, c in freq.items()]
    sizes  = list(freq.values())
    if len(sizes) > TREEMAP_MAX_BOXES:
        labels, sizes = labels[:TREEMAP_MAX_BOXES], sizes[:TREEMAP_MAX_BOXES]
    colors = [plt.get_cmap("tab20")(i % 20) for i in range(len(sizes))]
    plt.figure(figsize=(12, 8))
    squarify.plot(sizes=sizes, label=labels, color=colors, alpha=.85)
    plt.title(f"Tag treemap for '{QUERY}'  (unique tags={len(freq)})")
    plt.axis("off"); plt.tight_layout(); plt.show()


def plot_bar(freq, n=BAR_TOP_N):
    top = freq.most_common(n)
    tags, counts = zip(*top)
    y = np.arange(len(tags))
    plt.figure(figsize=(10, 6))
    plt.barh(y, counts, color="steelblue")
    plt.gca().invert_yaxis()
    plt.yticks(y, tags, fontsize=9)
    plt.xlabel("Videos using tag")
    plt.title(f"Top {n} tags for '{QUERY}'")
    for i, c in enumerate(counts):
        plt.text(c + 0.4, i, str(c), va="center", fontsize=8)
    plt.tight_layout(); plt.show()


if __name__ == "__main__":
    import os
 
    yt = yt_service(API_KEY)
    ids = search_top_ids(yt, QUERY, MAX_RESULTS)

    rows = fetch_metadata(yt, ids)

    save_metadata(rows, CSV_OUT)

    stats = tag_stats(rows)

    print(f" • 0 tags : {stats['no_tag']} ({stats['pct_no_tag']:.1f}%)")
    print(f" • 1-5 tags : {stats['le5']} ({stats['pct_le5']:.1f}%)")
    print(f" • ≥1 tag : {stats['with_tag']}/{stats['total']} "
        f"({stats['pct_with_tag']:.1f}%)")
    print(f" • >5 tags  : {stats['gt5']} ({stats['pct_gt5']:.1f}%)\n")

    append_run_summary(QUERY, stats, SUMMARY_CSV)

    freq = tag_frequency(rows)
    if freq:
        plot_treemap(freq)
        if len(freq) > TREEMAP_MAX_BOXES:
            plot_bar(freq, BAR_TOP_N)
    else:
        print("No tags found – skipping tag plots.")

