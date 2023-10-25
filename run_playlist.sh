#!/bin/zsh
# 
# This script is designed to run the program under Linux, MacOS operating systems.
# The python package virtualenv and its extension virtualenvwrapper need to be installed.
# Do not forget to set attributes on this file:
# > chmod u+x run_playlist.sh
#
# create Python virtual environment: 
# > mkvirtualenv playlist_m3u
#
# and edit this line to specify the correct path to where you have cloned the MassYoutubePlaylistDownloader repository:
# cd ~/MassYoutubePlaylistDownloader

source /usr/local/bin/virtualenvwrapper.sh

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <Username> [--format <Output file format>] [--output-dir <File saving folder>]"
    echo "Example: $0 @Username --format mp4 --output-dir ~/Downloads"
    echo "or"
    echo "Example: $0 @Username"
    exit 1
fi

username="$1"
video_format="mp4"
output_dir="~/Downloads"

while [[ $# -gt 1 ]]; do
    case "$2" in
        --format)
            video_format="$3"
            shift
            ;;
        --output-dir)
            output_dir="$3"
            shift
            ;;
        *)
            echo "Unknown parameter: $2"
            exit 1
            ;;
    esac
    shift
done

workon playlist_m3u
cd ~/MassYoutubePlaylistDownloader
python3 playlist_vlc.py "$username" --format "$video_format" --output-dir "$output_dir"
