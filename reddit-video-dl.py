#!/usr/bin/python
import sys
import re
import requests
import time
import shutil
import subprocess
import os
import argparse
import pathlib
import math

"""
TODO:
    - Quality selection from DASH playlist.
    - Error check before subprocess.
"""

config = {
    'USER_AGENT' : 'reddit-video-dl',
    'REDDIT_DOMAINS' : ['reddit.com', 'redd.it'],
    'OUTPUT_DIR' : r'',
    'FFMPEG_BINARY' : r''
}

def main(args):
    url = args.post

    # Check if domain is in list of reddit domains.
    if any(domain.lower() in url.lower() for domain in config['REDDIT_DOMAINS']):
        response = request_url(url)
        if response.status_code == 200:
            json = request_url('{}.json'.format(response.url)).json()
            data = json[0]['data']['children'][0]['data']
            reddit_video = data['media']['reddit_video']

            # is_gif: does the video have sound or not.
            # fallback_url: link to video in the largest resolution.
            # video_url: redd.it shortended url to video - redirects to reddit.com post.
            # playlist_url: DASH playlist file in XML format.

            is_gif = reddit_video['is_gif']
            fallback_url = reddit_video['fallback_url']
            video_url = data['url']
            playlist_url = reddit_video['dash_url']

            # Regex to split url after redd.it to get viedo id.
            video_id = re.search(r'redd.it\/(\w+)', video_url).group(1)

            # Reddit videos have audio and video split so we need to download the parts and mux them together via FFMPEG.
            video_file = '{}-video.mp4'.format(video_id)
            if is_gif or args.video:
                video_file = '{}-unencoded.mp4'.format(video_id)

            download_file(fallback_url, video_file)

            if is_gif or args.video:
                # Run the videos through FFMPEG so they are supported by WhatsApp...
                # idk it just works
                encode(video_id)
            else:
                # If video has audio find and download the audio.
                audio_loc = 'http://v.redd.it/{}/audio'.format(video_id)
                audio_file = '{}-audio.mp4'.format(video_id)
                download_file(audio_loc, audio_file)

                # Merge audio and video via FFMPEG.
                merge(video_id)

            # Remove all temp files.
            cleanup(video_id)

            print('Encoded and saved file {}.mp4'.format(video_id))
    else:
        print('ERROR: Not a reddit domain, exiting program.')
        sys.exit()


def request_url(url, **kwargs):
    """request_url - Handles requesting of webpages and files with error handling.
    Arguments:
      - url : URL of requested page or file.
      - kwargs : Keywork Arguments for request e.g. 'stream=True'
    Returns:
      - response : Request library response.
    """
    try:
        response = requests.get(url, headers={'User-agent': config['USER_AGENT']}, **kwargs)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        if status_code == 404:
            print('ERROR: 404 : "{}", exiting program.'.format(url))
        elif status_code == 429:
            print('ERROR: 429 : "{}". Connection rejected by server, exiting program. \n\
                If this error persits try changing USER_AGENT to something unique'.format(url))
        sys.exit()
    except requests.exceptions.Timeout as e:
        print('ERROR: Request to "{}" has timed out, exiting program.'.format(url))
        sys.exit()
    return response


def download_file(url, filename):
    """download_file - Handles downloading of file from http url.http
    Arguments:
      - url : URL of requested file.
      - filename : Name of file being saved.
    """
    response = request_url(url, stream=True)
    size = int(response.headers['Content-length'])
    print('Downloading {}, size: {}'.format(filename, format_length(size)))

    with open('{}'.format(filename), 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)
    del response


def format_length(length):
    # Formats bytes into KB or MB
    if length == 0:
        return '0B'
    size_name = ('B', 'KB', 'MB')
    i = int(math.floor(math.log(length, 1024)))
    p = math.pow(1024, i)
    s = round(length / p, 2)
    return '{} {}'.format(s, size_name[i])


def cleanup(video_id):
    print('Removing temporary files.')

    files = [
        '{}-audio.mp4'.format(video_id),
        '{}-unencoded.mp4'.format(video_id),
        '{}-video.mp4'.format(video_id)
    ]

    # Check if file exists then delete it.
    for file in files:
        if os.path.isfile(file):
            print(' - Deleting {}'.format(file))
            os.remove(file)


def encode(video_id):
    output_path = os.path.normpath('{}/{}'.format(config['OUTPUT_DIR'], video_id))
    cmd = 'ffmpeg -y -i {0}-unencoded.mp4 -c copy {1}.mp4'.format(video_id, output_path)
    run_ffmpeg(cmd)
    print('Encoding finished.')


def merge(video_id):
    audio_file = '{}-video.mp4'.format(video_id)
    video_file = '{}-audio.mp4'.format(video_id)
    output_path = os.path.normpath('{}/{}'.format(config['OUTPUT_DIR'], video_id))
    cmd = 'ffmpeg -y -i {0} -i {1} -c copy {2}.mp4'.format(audio_file, video_file, output_path)
    run_ffmpeg(cmd)


def run_ffmpeg(cmd):
    proc = run_cmd(cmd)


def run_cmd(cmd):
    # Supress FFmpeg console output.
    FNULL = open(os.devnull, 'w')
    kwargs = {
        'shell' : True,
        'stdout' : FNULL,
        'stderr' : subprocess.STDOUT
    }

    if os.name == 'nt':
        kwargs = { 'creationflags' : 0x08000000 }

    proc = subprocess.Popen(cmd, **kwargs)
    proc.communicate()
    return proc


def check_ffmpeg(cmd):
    try:
        run_cmd(cmd)
    except Exception as e:
        return False
    else:
        return True


if __name__ == '__main__':
    parse = argparse.ArgumentParser()
    parse.add_argument('-p', '--post', help='Reddit video post.')
    parse.add_argument('-o', '--out', help='Output directory.')
    parse.add_argument('-v', '--video', help='Download video only.', action='store_true')
    args = parse.parse_args()

    # If no Reddit post given, exit program.
    if args.post is None:
        print('ERROR: No Reddit post given. Use argument -h for help. Exiting program.')
        sys.exit()

    # Check if FFmpeg exists.
    if config['FFMPEG_BINARY'] == '':
        if not check_ffmpeg('ffmpeg'):
            print('ERROR: Can\'t find FFmpeg binary, try setting "FFMPEG_BINARY" in config. Exiting program.')
            sys.exit()
    else:
        if not check_ffmpeg(config['FFMPEG_BINARY']):
            print('ERROR: Can\'t find FFmpeg binary. Double check "FFMPEG_BINARY". Exiting program.')
            sys.exit()

    # Set output directory to be -o if set
    # Or set the output as the 'working dir/output' if OUTPUT_DIR is empty
    if args.out is not None:
        config['OUTPUT_DIR'] = os.path.normpath(args.out)
    elif config['OUTPUT_DIR'] == '':
        d_output = os.path.normpath('{}/output'.format(os.getcwd()))
        config['OUTPUT_DIR'] = d_output

    # Create OUTPUT_DIR if doesn't exist.
    if not os.path.exists(config['OUTPUT_DIR']):
        print('Output directory doesn\'t exist.\nCreating "{}".'.format(config['OUTPUT_DIR']))
        try:
            pathlib.Path(config['OUTPUT_DIR']).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            if e.errno == 13:
                print('ERROR: Access denied while creating directory "{}". Exiting program.'.format(config['OUTPUT_DIR']))
                sys.exit()

    print('Saving file to {}'.format(config['OUTPUT_DIR']))
    main(args)
