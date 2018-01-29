## reddit-video-dl

Reddit Video downloader made with Python and using FFMPEG for Linux and Windows.

Requirements:
* Python 3
* FFmpeg

To set a permanent output directory, set the `OUTPUT_DIR` variable to your desired directory.

Arguments
```
  -p POST, --post POST  Reddit video post
  -o OUT, --out OUT     Output directory.
```

For example:

````python reddit-video-dl.py -p https://www.reddit.com/r/trashpandas/comments/7ry91x/so_close_yet_so_far/````
