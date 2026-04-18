import sys
import requests
import json


def run():
    if len(sys.argv) < 2:
        return

    path = sys.argv[1]
    url = "http://127.0.0.1:8000/api/files/publish"

    try:
        response = requests.post(url, json={"local_path": path})
        if response.status_code == 200:
            pass
    except Exception as e:
        with open("/tmp/cf_error.log", "a") as f:
            f.write(str(e) + "\n")


if __name__ == "__main__":
    run()