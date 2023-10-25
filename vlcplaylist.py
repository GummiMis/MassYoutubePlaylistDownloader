class VLCPlaylistGenerator:
    def __init__(self, output_folder, playlist_name):
        self.output_folder = output_folder
        self.playlist_name = playlist_name
        self.entries = []

    def add_entry(self, video_name, video_path):
        self.entries.append((video_name, video_path))

    def generate_playlist(self):
        playlist_path = f"{self.output_folder}/{self.playlist_name}"
        with open(playlist_path, "w") as playlist_file:
            for video_name, video_path in self.entries:
                playlist_file.write(f"#EXTINF:-1,{video_name}\n")
                playlist_file.write(video_path + "\n")
