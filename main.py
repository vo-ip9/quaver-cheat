# quaver cheating script for acquiring ill begotten gains

# by vo-ip9
# discord @vondeehair
# you will get banned if you use this publicly

# FEATURES
# built-in CLI menu for navigating all your downloaded songs and their difficulties
# automatically parses the selected song + difficulty's .qua file
# song speed can be changed by the user to reflect any in-game speed changes
# script will wait until a key press (default: space) to start playing automatically
# (make sure to time this precisely on the first note)

import os
import time
import yaml
import inquirer
import keyboard
import threading
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class HitObject:
    start_time: int
    lane: int
    key: str
    end_time: Optional[int] = None # only needed for hold notes

    @property
    def is_hold_note(self) -> bool:
        return self.end_time is not None

    @property
    def duration(self) -> int:
        if self.is_hold_note:
            return self.end_time - self.start_time
        return 0


class AutoPlayer:
    def __init__(self, hit_objects: List[HitObject], tap_duration_ms: int = 50):
        self.hit_objects = sorted(hit_objects, key=lambda x: x.start_time)
        self.is_playing = False
        self.start_time = None
        self.current_index = 0
        self.held_keys = set()
        self.tap_duration_ms = tap_duration_ms

    def start_auto_play(self, trigger="space"):
        print(f"auto player ready, press {trigger} to start...")

        keyboard.wait(trigger)
        self.start_time = time.time() * 1000
        self.is_playing = True
        self.current_index = 0

        auto_thread = threading.Thread(target=self.auto_play_loop, daemon=True)
        auto_thread.start()
        print("auto player started.")

        while self.is_playing:
            if keyboard.is_pressed("q"):
                self.stop_auto_play()
                break
            time.sleep(0.01)

    def auto_play_loop(self):
        while self.is_playing and self.current_index < len(self.hit_objects) or self.held_keys:
            current_time = time.time() * 1000 - self.start_time
            self.check_and_press_notes(current_time)
            self.check_and_release_hold_notes(current_time)
            time.sleep(0.001) # 1ms

        self.release_all_held_keys()
        self.is_playing = False
        print("auto play finished.")

    def check_and_press_notes(self, current_time: float):
        delay = 5 # act 5 ms before actual time processing delay
        while (self.current_index < len(self.hit_objects) and
               self.hit_objects[self.current_index].start_time <= current_time + delay):

            note = self.hit_objects[self.current_index]
            self.press_key(note)

            if note.is_hold_note:
                self.held_keys.add(note)
            self.current_index += 1

    def check_and_release_hold_notes(self, current_time: float):
        keys_to_release = []

        for held_note in self.held_keys:
            if current_time >= held_note.end_time:
                self.release_key(held_note)
                keys_to_release.append(held_note)

        for key in keys_to_release:
            self.held_keys.remove(key)

    def press_key(self, note: HitObject):
        try:
            keyboard.press(note.key)

            if not note.is_hold_note:
                def delayed_release():
                    time.sleep(self.tap_duration_ms / 1000.0)
                    keyboard.release(note.key)

                release_thread = threading.Thread(target=delayed_release, daemon=True)
                release_thread.start()

            print(f"\rpressing '{note.key}'    ", end="\r")
        except Exception as e:
            print(f"error pressing key '{note.key}': {e}")

    def release_key(self, note: HitObject):
        try:
            keyboard.release(note.key)
            print(f"\rreleasing '{note.key}'   ", end="\r")
        except Exception as e:
            print(f"error releasing key '{note.key}': {e}")

    def release_all_held_keys(self):
        for held_note in self.held_keys:
            try:
                keyboard.release(held_note.key)
                print(f"force released '{held_note.key}'")
            except:
                pass
        self.held_keys.clear()

    def stop_auto_play(self):
        self.is_playing = False
        self.release_all_held_keys()
        print("auto play stopped.")


def parse_beatmap(yaml_content: str, MAPPING: dict) -> List[HitObject]:

    data = yaml.safe_load(yaml_content)
    raw_objects = []

    for object_data in data.get("HitObjects", []):
        start_time = object_data.get("StartTime", 0)
        lane = object_data.get("Lane")
        end_time = object_data.get("EndTime", None)

        if lane and 1 <= lane <= len(MAPPING):
            raw_objects.append((start_time, lane, end_time))

    if raw_objects:
        first_note_time = min(obj[0] for obj in raw_objects)
    else:
        first_note_time = 0

    hit_objects = []
    for start_time, lane, end_time in raw_objects:
        key = MAPPING[lane]
        hit_object = HitObject(
            start_time=start_time - first_note_time,
            lane=lane,
            key=key,
            end_time=end_time - first_note_time if end_time is not None else None
        )
        hit_objects.append(hit_object)
    return sorted(hit_objects, key=lambda x : x.start_time)


def change_song_speed(factor: float, hit_objects, MAPPING: dict):
    new_hit_objects = []
    for hit_object in hit_objects:
        key = MAPPING[hit_object.lane]
        new_hit_object = HitObject(
            start_time=hit_object.start_time / factor,
            lane=hit_object.lane,
            key=key,
            end_time=hit_object.end_time / factor if hit_object.end_time is not None else None
        )
        new_hit_objects.append(new_hit_object)
    return sorted(new_hit_objects, key=lambda x : x.start_time)


def get_quaver_path():
    possible_steam_paths = [
        os.path.join(os.path.expanduser("~"), "Steam", "steamapps", "common"),
        r"C:\Program Files (x86)\Steam\steamapps\common",
        r"C:\Program Files\Steam\steamapps\common",
        r"D:\Steam\steamapps\common",
        r"E:\Steam\steamapps\common"]

    for path in possible_steam_paths:
        quaver_path = os.path.join(path, "Quaver", "Songs")
        if os.path.exists(quaver_path) and os.path.isdir(quaver_path):
            return quaver_path


def get_difficulties(song_path):
    files = [f for f in os.listdir(song_path) if f.endswith(".qua")]
    difficulties = []

    for file in files:
        with open(os.path.join(song_path, file), "r", encoding="utf-8") as f:
            for line in f:
                if "DifficultyName:" in line:
                    difficulties.append(line.split(":", 1)[1].strip())
                    break
    return difficulties, files


def get_all_songs_info(songs_path: str, tag: str):
    song_folders = [f for f in os.listdir(songs_path) if os.path.isdir(os.path.join(songs_path, f))]
    info = []
    folder_names = []

    for folder in song_folders:
        first_qua_file = [f for f in os.listdir(os.path.join(songs_path, folder)) if f.endswith(".qua")][0]
        with open(os.path.join(songs_path, folder, first_qua_file), "r", encoding="utf-8") as f:
            found = False
            for line in f:
                if tag in line:
                    info.append(line.split(":",1)[1].strip())
                    folder_names.append(folder)
                    found = True
                    break
            if not found:
                print(f"could not find {tag} in {first_qua_file}.")
    return info, folder_names


def main():
    if quaver_path := get_quaver_path():
        print(f"found quaver songs path at {quaver_path}")
    else:
        quaver_path = input(f"quaver songs path not found. please enter the path:").replace("\"", "")

    song_titles, title_folders = get_all_songs_info(quaver_path, "Title:")
    song_artists, artist_folders = get_all_songs_info(quaver_path, "Artist:")

    if len(song_titles) != len(song_artists) or title_folders != artist_folders:
        print("error reading artist & song title info.")
        return

    max_artist_length = max(len(artist) for artist in song_artists)
    display_names = [f"{song_artists[i]:<{max_artist_length}} - {song_titles[i]}" for i in range(len(song_titles))]
    questions = [inquirer.List("song", message="select song", choices=display_names)]
    song_choice = inquirer.prompt(questions)["song"]

    selected_folder = title_folders[display_names.index(song_choice)]
    song_path = os.path.join(quaver_path, selected_folder)
    os.system("cls")

    difficulties, files = get_difficulties(song_path)
    questions = [inquirer.List("difficulty", message="select difficulty", choices=difficulties)]
    song_path = os.path.join(song_path, files[difficulties.index(inquirer.prompt(questions)["difficulty"])])

    with open(song_path, "r", encoding="utf-8") as f:
        for line in f:
            if "Keys4" in line:
                MAPPING = {1: "a", 2: "s", 3: ";", 4: "'"}
                print(f"4k mapping: |{MAPPING[1]}|{MAPPING[2]}|{MAPPING[3]}|{MAPPING[4]}|")
            elif "Keys7" in line:
                MAPPING = {1: "a", 2: "s", 3: "d", 4: "space", 5: "j", 6: "k", 7: "l"}
                print(f"7k mapping: |{MAPPING[1]}|{MAPPING[2]}|{MAPPING[3]}|{MAPPING[4]}|{MAPPING[5]}|{MAPPING[6]}|{MAPPING[7]}|")
        f.seek(0)
        hit_objects = parse_beatmap(f.read(), MAPPING)

    print(f"done parsing {len(hit_objects)} hit objects (notes)")
    change_speed = True if input("change speed? (y/n): ").lower() == "y" else False
    if change_speed:
        factor = float(input("x"))
        hit_objects = change_song_speed(factor, hit_objects, MAPPING)
    auto_player = AutoPlayer(hit_objects)
    auto_player.start_auto_play("space")


if __name__ == "__main__":
    main()
