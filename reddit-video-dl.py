#!/usr/bin/python
import sys
import re
import requests
import time
import shutil
import subprocess
import os

USER_AGENT = 'reddit-video-dl'
REDDIT_DOMAINS = ['reddit.com', 'redd.it']
OUTPUT_DIR = r''

def main():
    url = sys.argv[1]

    # Check if domain is in list of reddit domains.
    if any(domain.lower() in url.lower() for domain in REDDIT_DOMAINS):
        response = request_url(url)

        if response.status_code == 404:
            print('Invalid URL')
            return

        # If request is rejected by server try again in 5 seconds.
        while response.status_code != 200:
            print('Error: Trying again in 5 seconds.')
            response = request_url(url)
            time.sleep(5)

        if response.status_code == 200:
            # is_gif: does the video have sound or not.
            # fallback_url: link to video in the largest resolution.
            # video_url: redd.it shortended url to video - redirects to reddit.com post.

            json = request_url('{}.json'.format(response.url)).json()
            is_gif = json[0]['data']['children'][0]['data']['media']['reddit_video']['is_gif']
            fallback_url = json[0]['data']['children'][0]['data']['media']['reddit_video']['fallback_url']
            video_url = json[0]['data']['children'][0]['data']['url']

            # Regex to split url after .it to get viedo id.
            video_id = re.search(r'redd.it\/(\w+)', video_url).group(1)

            # Reddit videos are audio and video split so we need to download the parts and mux them together via FFMPEG.
            video_file = '{}-video.mp4'.format(video_id)
            if is_gif:
                video_file = '{}-unencoded.mp4'.format(video_id)

            print('Downloading video.')
            download_file(fallback_url, video_file)

            if is_gif:
                # Run the videos through FFMPEG so they are supported by WhatsApp...
                # idk it just works
                encode(video_id)
            else:
                print('Downloading audio.')
                audio_loc = 'http://v.redd.it/{}/audio'.format(video_id)
                audio_file = '{}-audio.mp4'.format(video_id)
                download_file(audio_loc, audio_file)

                # Merge audio and video via FFMPEG.
                merge(video_id)

            # Remove all temp files downloaded.
            cleanup(video_id)

            print('Encoded and saved file {}.mp4'.format(video_id))
    else:
        print('Not a reddit domain.')
        return


def cleanup(video_id):
    print('Removing temporary files.')

    files = [
        '{}-audio.mp4'.format(video_id),
        '{}-unencoded.mp4'.format(video_id),
        '{}-video.mp4'.format(video_id)
    ]

    for file in files:
        if os.path.isfile(file):
            os.remove(file)


def encode(video_id):
    cmd = 'ffmpeg -y -i {0}-unencoded.mp4 -c copy "{1}{0}.mp4"'.format(video_id, OUTPUT_DIR)
    subprocess.call(cmd, shell=True)
    print('Encoding Done')


def merge(video_id):
    audio_file = '{}-video.mp4'.format(video_id)
    video_file = '{}-audio.mp4'.format(video_id)
    output_file = '{}.mp4'.format(video_id)

    cmd = 'ffmpeg -y -i {0} -i {1} -c copy "{3}{2}"'.format(
        audio_file, video_file, output_file, OUTPUT_DIR)
    subprocess.call(cmd, shell=True)
    print('Finished muxing audio and visual.')


def request_url(url):
    return requests.get(url, headers={'User-agent': USER_AGENT})


def download_file(url, filename):
    response = requests.get(url, stream=True)
    with open('{}'.format(filename), 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)
    del response


if __name__ == '__main__':
    main()
