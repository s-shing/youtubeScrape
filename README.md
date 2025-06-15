# YOUTUBE DOWNLOAD SCRAPER
## Quickstart
create a .env file with YT_API_KEY="{api key}" or replace DEVELOPER_KEY = os.environ["YT_API_KEY"] with DEVELOPER_KEY = {api key}  where {api key} is your youtube v3 api key
ensure path to .env is set as .env

you may need to install ffmpeg if video and audio is not merging during download. see here: https://www.wikihow.com/Install-FFmpeg-on-Windows

read through ytmain to see available presets. alternatively, directly call util functions

Filenames are based on video ID while foldernames are based on channels.

## Parameters
In the code, you can 

toggle download, comments, thumbnail, and captions separately

change filter date

change file to pull from

change file to write to

