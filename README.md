# YouTube Mass Playlist Downloader

"YouTube Mass Playlist Downloader" is a Python script designed for mass downloading of playlists from the YouTube channel of a specified user. Depending on the selected format, the script generates video or audio playlists in the m3u format for VLC Player. The generated playlists are stored in the directory specified at the script's launch, where a subfolder with the name of the YouTube channel is created. Downloaded media files are stored in the respective subdirectories.


## Installation

1. Clone this repository:
   ```shell
   git clone https://github.com/GummiMis/MassYoutubePlaylistDownloader
   ```

2. Install the required packages using pip (possibly using a virtual environment):
    ```shell
    pip install -r requirements.txt
    ```

## Usage

To use the YouTube Playlist Downloader, run the script with the following command:
   ```shell
   playlist_m3u.py [-h] [--format FORMAT] [--output-dir OUTPUT_DIR] url
   ```

   - &lt;FORMAT&gt;: The desired video format (default is "mp4").
   - &lt;OUTPUT_DIR&gt;: The root directory for hosting the download and playlist files.
   - &lt;url&gt;: The URL of the YouTube channel or the username of the channel's founder.

Example:
   ```shell
   python playlist_m3u.py https://www.youtube.com/@username --format mp4 --output-dir ~/Downloads
   ```

## License
This project is licensed under the [GPL License](https://github.com/GummiMis/MassYoutubePlaylistDownloader/blob/main/LICENSE) - see the LICENSE file for details.
