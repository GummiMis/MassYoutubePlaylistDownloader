import os
import argparse
import concurrent.futures
import re
import sys
from pytube import YouTube
from pytube.exceptions import VideoPrivate, MembersOnly, AgeRestrictedError
from playwright.sync_api import sync_playwright
from vlcplaylist import VLCPlaylistGenerator
import ssl


class YouTubePlaylistDownloader:
    def __init__(self, url, video_format, output_dir):
        ssl._create_default_https_context = ssl._create_stdlib_context
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

    @staticmethod
    def __scroll_page(page, selector):
        num_selector = 0
        try:
            page.wait_for_selector(selector, timeout=500)
            while True:
                selectors = page.query_selector_all(selector)
                if num_selector == len(selectors):
                    break
                else:
                    num_selector = len(selectors)
                    page.mouse.wheel(0, page.viewport_size["height"] * 5)
                    page.wait_for_timeout(1000)
            if len(selectors) > 0:
                return selectors
            else:
                return None
        except:
            return None

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
            print("Starting collecting playlists...")
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(self.url)
                page.wait_for_load_state("domcontentloaded", timeout=5000)
                lang_selector = page.get_by_role("button", name="Down arrow")
                if lang_selector.count():
                    lang_selector.click()
                    page.get_by_role("menuitem", name="English", exact=True).click()
                    page.get_by_role("button", name="Accept all").click()
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                    attempts = 0
                while attempts < 5:
                    playlists = self.__scroll_page(
                        page, "#details.style-scope.ytd-grid-playlist-renderer"
                    )
                    if playlists != None:
                        break
                    page.goto(self.url)
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                    attempts += 1
                if playlists != None:
                    data = []
                    for index, playlist in enumerate(playlists, start=1):
                        playlist_name = (
                            "{:02d}-".format(index)
                            + f'{self.__sanitize_name(playlist.query_selector("h3 a").text_content().strip())}_{self.video_format}.m3u'
                        )
                        playlist_url = f'https://www.youtube.com{playlist.query_selector("#view-more a").get_attribute("href")}'
                        data.append({"playlist": playlist_name, "url": playlist_url})
                    # playlists = None
                    print("Playlist Collected!\nStarting collecting videos...")
                    full_data = data.copy()
                    for index, playlist in enumerate(data):
                        attempts = 0
                        while attempts < 5:
                            page.goto(playlist["url"])
                            page.wait_for_load_state("domcontentloaded", timeout=5000)
                            videos_list = self.__scroll_page(page, "div h3 a")
                            if videos_list != None:
                                break
                            attempts += 1
                        video_data = []
                        if videos_list != None:
                            for num_video, video in enumerate(videos_list, start=1):
                                video_name = (
                                    "{:02d}-".format(num_video)
                                    + f"{self.__sanitize_name(video.text_content().strip())}"
                                )
                                video_href = video.get_attribute("href")
                                video_url = (
                                    f"https://www.youtube.com{video_href.split("&")[0]}"
                                )
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
                    if videos_list != None:
                        page.close()
                        browser.close()
                        print("Videos Collected!\nStarting downloading videos...")
                        self.process_playlists(full_data)
                        print("Download Completed!")
                    else:
                        print("Something went wrong!")
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
