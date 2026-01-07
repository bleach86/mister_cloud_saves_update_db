#! /usr/bin/env python3

import os
import sys
import hashlib
import json
import time
import tempfile
import requests  # type: ignore

GH_REPO_API_URL = (
    "https://api.github.com/repos/bleach86/mister_cloud_saves/releases/latest"
)
SCRIPT_RAW_URL = "https://raw.githubusercontent.com/bleach86/mister_cloud_saves/refs/heads/main/scripts/cloud_saves.sh"
UPDATE_DB_FILE = "mister_cloud_saves_db.json"


def compute_file_hash(file_path, hash_algo="md5"):
    """Compute the hash of a file using the specified hashing algorithm.

    Keyword arguments:
    file_path -- path to the file to be hashed
    hash_algo -- hashing algorithm to use (default is "md5")
    Return: hexadecimal digest of the hash
    """

    hash_func = hashlib.new(hash_algo)
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)
    return hash_func.hexdigest()


def get_tag_and_latest_release_url():
    """
    Gets the latest release download URL from GitHub.

    :return: Download URL string
    """

    response = requests.get(GH_REPO_API_URL, timeout=30)
    if response.status_code == 200:
        data = response.json()
        tag_name = data.get("tag_name", "unknown")

        for asset in data.get("assets", []):
            if asset.get("name") == "client.tar.xz":
                return (asset.get("browser_download_url"), tag_name)

    print("Error fetching latest release info")
    sys.exit(1)


def get_file_hash_and_size(download_url):
    """
    Downloads a file from the given URL and computes its size and MD5 hash.

    Keyword arguments:
    argument -- description
    Return: return_description
    """

    with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
        response = requests.get(download_url, stream=True, timeout=60)
        if response.status_code == 200:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            tmp_file.flush()
            size = os.path.getsize(tmp_file.name)
            file_hash = compute_file_hash(tmp_file.name, "md5")
            return size, file_hash

        print("Error downloading client file")
        sys.exit(1)


def generate_update_db():
    """Generates the update database dictionary.

    Keyword arguments:
    argument -- description
    Return: return_description
    """

    update_db = get_update_db_schema()

    client_download_url, _ = get_tag_and_latest_release_url()

    # Update timestamp
    update_db["timestamp"] = int(time.time())

    # Update script file info
    script_size, script_hash = get_file_hash_and_size(SCRIPT_RAW_URL)
    update_db["files"]["Scripts/cloud_saves.sh"]["size"] = script_size
    update_db["files"]["Scripts/cloud_saves.sh"]["hash"] = script_hash
    update_db["files"]["Scripts/cloud_saves.sh"]["url"] = SCRIPT_RAW_URL

    # Update client file info
    client_size, client_hash = get_file_hash_and_size(client_download_url)
    update_db["files"]["cloud_saves/updates/client.tar.xz"]["size"] = client_size
    update_db["files"]["cloud_saves/updates/client.tar.xz"]["hash"] = client_hash
    update_db["files"]["cloud_saves/updates/client.tar.xz"]["url"] = client_download_url

    return update_db


def get_update_db_schema():
    """Returns the update database schema as a dictionary."""

    return {
        "v": 1,
        "db_id": "mister_cloud_saves",
        "timestamp": 0,
        "files": {
            "Scripts/cloud_saves.sh": {
                "size": 0,
                "hash": "",
                "url": "",
                "tags": [1],
            },
            "cloud_saves/updates/client.tar.xz": {
                "size": 0,
                "hash": "",
                "url": "",
                "reboot": True,
                "tags": [0],
            },
        },
        "folders": {"Scripts": {}, "cloud_saves": {}, "cloud_saves/updates": {}},
        "tags_dictionary": {"cloudsaves": 0, "scripts": 1},
    }


def save_update_db_to_file_if_changed(update_db, file_path):
    """Saves the update database to a file if it has changed.
    Keyword arguments:
    update_db -- the update database dictionary
    file_path -- path to the file where the database should be saved
    """

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            existing_db = json.load(f)
        if existing_db == update_db:
            print("No changes detected in the update database.")
            return

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(update_db, f, indent=4)
    print(f"Update database saved to {file_path}.")


def main():
    """Main function to generate and save the update database."""

    update_db = generate_update_db()
    save_update_db_to_file_if_changed(update_db, UPDATE_DB_FILE)


if __name__ == "__main__":
    main()
