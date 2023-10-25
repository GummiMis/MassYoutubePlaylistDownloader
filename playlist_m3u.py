import os
import argparse
import concurrent.futures
import re
import sys
from pytube import YouTube
from pytube.exceptions import VideoPrivate, MembersOnly, AgeRestrictedError
from playwright.sync_api import sync_playwright
from vlcplaylist import VLCPlaylistGenerator


class YouTubePlaylistDownloader:
    def __init__(self, url, video_format, output_dir):
        username = self.__extract_username(url)
        if username:
            self.url = f"https://youtube.com/@{username}/playlists"
            self.video_format = video_format.lower()
            self.destination_folder = f"{os.path.expanduser(output_dir)}/{username}"
            if self.video_format == "mp4":
                self.output_path = f"{self.destination_folder}/Videos"
            elif self.video_format == "mp3":
                self.output_path = f"{self.destination_folder}/Audios"
            else:
                print(
                    f'Warning: Invalid format: {self.video_format} of download files!\nValid type format is only "MP4" or "MP3"!'
                )
                sys.exit()
        else:
            print(
                f"Warning: Invalid channel or username! \n{url}\n Please enter only the channel link or username:\nhttps://www.youtube.com/@User or @User"
            )
            sys.exit()

    @staticmethod
    def __extract_username(url):
        pattern = r"^https://www\.youtube\.com/(?:@)?([\w-]+)$|^@([\w-]+)$|^([\w-]+)$"
        match = re.match(pattern, url)
        if match:
            for group in match.groups():
                if group:
                    return group
        return None

    @staticmethod
    def __sanitize_name(name):
        name = re.sub(r"\s+", " ", name).strip()
        name = re.sub(r'[\/:*?"<>| .]', "_", name)
        sanitized = re.sub(r"__+", "-", name).strip()
        return sanitized

    def extract_data(self, data):
        results = []
        if isinstance(data, dict):
            if "videoId" in data and "simpleText" in data.get("headline", {}):
                results.append((data["videoId"], data["headline"]["simpleText"]))
            for key, value in data.items():
                results.extend(self.extract_data(value))
        elif isinstance(data, list):
            for item in data:
                results.extend(self.extract_data(item))
        return results

    def collect_playlists(self):
        if hasattr(self, "destination_folder"):
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(self.url)
                page.wait_for_load_state("load", timeout=5000)
                page.keyboard.press("Control+ArrowDown")
                lang_selector = page.get_by_role("button", name="Down arrow")
                if lang_selector.count():
                    # If the element with terms of use is found, switch the language of the page to "English" and click on the "Accept all" button
                    lang_selector.click()
                    page.get_by_role("menuitem", name="English", exact=True).click()
                    page.get_by_role("button", name="Accept all").click()
                    page.wait_for_load_state("load", timeout=5000)
                # To load the whole page, we try swiping it 5 times just in case
                for i in range(5):
                    page.keyboard.press("Control+ArrowDown")
                    i += 1
                data = []
                playlists = page.query_selector_all("#items #details")
                for index, playlist in enumerate(playlists, start=1):
                    playlist_name = (
                        "{:02d}-".format(index)
                        + f'{self.__sanitize_name(playlist.query_selector("h3 a").text_content().strip())}_{self.video_format}.m3u'
                    )
                    playlist_url = f'https://www.youtube.com{playlist.query_selector("#view-more a").get_attribute("href")}'
                    data.append({"playlist": playlist_name, "url": playlist_url})
                full_data = data.copy()
                for index, playlist in enumerate(data):
                    page.goto(playlist["url"])
                    page.wait_for_selector("div h3 a", timeout=2000)
                    # We are now on page one of the playlists, ready for parsing.
                    for i in range(5):
                        page.keyboard.press("Control+ArrowDown")
                        i += 1
                    video_data = []
                    videos_list = page.query_selector_all("div h3 a")
                    for video in videos_list:
                        video_name = (
                            f"{self.__sanitize_name(video.text_content().strip())}"
                        )
                        video_href = video.get_attribute("href")
                        if "&" in video_href:
                            video_href = video_href.split("&")[0]
                        video_url = f"https://www.youtube.com{video_href}"
                        video_id = (
                            video_href.split("&")[0].split("v=")[-1].split("/")[-1]
                        )
                        video_data.append(
                            {
                                "video_name": video_name,
                                "video_url": video_url,
                                "video_id": video_id,
                            }
                        )
                    full_data[index].update({"videos": [video_data]})
                page.close()
                browser.close()
                self.process_playlists(full_data)
        else:
            print(f"Incorrect channel name!\nChannel name not found in {self.url}")

    def process_playlists(self, full_data):
        for single_playlist in full_data:
            print(
                f'\033[94mProcessing a playlist: {single_playlist["playlist"]}\033[0;0m'
            )
            playlist = VLCPlaylistGenerator(
                self.destination_folder, single_playlist["playlist"]
            )
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                for videos in single_playlist["videos"]:
                    for video in videos:
                        try:
                            video_file = f'{video["video_id"]}.{self.video_format}'
                            if self.video_format == "mp4":
                                video_path = f"./Video/{video_file}"
                            else:
                                video_path = f"./Audio/{video_file}"
                            playlist.add_entry(
                                video["video_name"],
                                video_path,
                            )
                            if not os.path.exists(f"{self.output_path}/{video_file}"):
                                yt = YouTube(video["video_url"])
                                streams = yt.streams
                                if self.video_format == "mp3":
                                    yt_stream = streams.filter(only_audio=True).first()
                                else:
                                    yt_stream = streams.get_highest_resolution()
                                future = executor.submit(
                                    self.__download_video,
                                    yt_stream,
                                    self.output_path,
                                    video_file,
                                    video["video_name"],
                                )
                                futures.append(future)
                            else:
                                print(f'Video {video["video_name"]} already exists')
                        except (
                            VideoPrivate,
                            MembersOnly,
                            AgeRestrictedError,
                        ):
                            print(
                                f'\033[93m\n\nVideo {video["video_name"]} is not allowed to be downloaded!\n\n\033[0;0m'
                            )
                concurrent.futures.wait(futures)
            playlist.generate_playlist()
        return True

    def __download_video(self, yt_stream, output_path, video_name, video_title):  #
        print(f"\033[92m Download video {video_title}\033[0;0m")
        yt_stream.download(output_path, video_name)
        print(f"Video {video_title} is downloaded")


def main():
    parser = argparse.ArgumentParser(description="Mass download YouTube playlists.")
    parser.add_argument(
        "url", help="URL of the YouTube channel or User name founder of channel"
    )
    parser.add_argument("--format", default="mp4", help="Video format (default: mp4)")
    parser.add_argument(
        "--output-dir",
        default="~/Downloads",
        help="Output directory for downloaded videos",
    )
    args = parser.parse_args()
    downloader = YouTubePlaylistDownloader(args.url, args.format, args.output_dir)
    downloader.collect_playlists()


if __name__ == "__main__":
    main()
