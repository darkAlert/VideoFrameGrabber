#!/bin/bash

SRC=/home/darkalert/Desktop/Boost/Projects/BallerTV/video/basketball/1
DST=/home/darkalert/Desktop/Boost/Projects/BallerTV/video/basketball/1_proc

python3 convert_videos.py ${SRC} ${DST} -c h264_nvenc -b 3.3M