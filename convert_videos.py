import argparse
import os
import shutil
import subprocess
import tarfile
from datetime import datetime
from random import randint
from subprocess import check_output
import cv2
import json


MAX_VIDEO_BITRATE = 3500000
TARGET_VIDEO_HEIGHT = 720
CODEC_BY_DEFAULT = 'h264'
PRESET_BY_DEFAULT = 'medium'


def get_base_name(path):
    return '.'.join(path.split('/')[-1].split('.')[:-1])


def change_ext(name, new_ext):
    name = '.'.join(name.split('.')[:-1])
    return name + new_ext


def run_extract_frames(src_video, dst_folder, amount_to_extract):
    cap = cv2.VideoCapture(src_video)
    if cap is None:
        print("Cannot read video " + src_video)
        return
    frames_amount = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    minp = int(0.1 * frames_amount)
    maxp = int(0.9 * frames_amount)
    nums = set()
    c = 0
    while len(nums) < amount_to_extract and c < 1000:
        c += 1
        num = randint(minp, maxp)
        nums.add(num)
        cap.set(cv2.CAP_PROP_POS_FRAMES, num)
        res, img = cap.read()
        if img is None :
            continue
        dst = os.path.join(dst_folder, "{}.png".format(num))
        cv2.imwrite(dst, img)


def get_video_info(src, verbose=False):
    cmd = 'ffprobe -loglevel 0 -print_format json -show_format -show_streams ' + src
    out = check_output(cmd.split()).decode("utf-8")
    info = json.loads(out)
    if verbose:
        print (out)

    return info


def run_ffmpeg(src, dst, params):
    if src is not None:
        cmd = ['ffmpeg', '-i', src]
    else:
        cmd = ['ffmpeg']
    params = params.split()
    if len(params):
        cmd += params
    cmd += [dst]
    print(' '.join(cmd))
    subprocess.Popen(cmd).wait()


def run_video_concat_with_ffmpeg(src_files, dst_file, codec=None, fps=None, preset=None,
                                 scale_720=False, bitrate=None, max_bitrate=None):
    # convert to temp files of same parameters
    temp_names = []
    for i, name in enumerate(src_files):
        temp_name = "temp{}.mp4".format(i+1)
        run_video_with_ffmpeg(name, temp_name, codec, fps=fps, preset=preset,
                              scale_720=scale_720, bitrate=bitrate, max_bitrate=max_bitrate)
        temp_names.append(temp_name)

    # make temporary concat.txt for merging clips
    file = open("concat.txt", "w")
    for name in temp_names:
        file.write('file ' + name + '\n')
    file.close()

    # convert to a single file
    params = "-f concat -safe 0 -i concat.txt -c copy"
    run_ffmpeg(None, dst_file, params)

    # remove temp files
    for name in temp_names:
        os.remove(name)
    os.remove("concat.txt")


def run_video_with_ffmpeg(src_file, dst_file, codec=None, fps=None, preset=None,
                          scale_720=False, bitrate=None, max_bitrate=None, start=None, end=None):
    '''
    :param src_file:   Source video path
    :param dst_file:   Destination video path
    :param fps: Target FPS
    :param preset:     Encoding speed (ultrafast, superfast, veryfast, faster, fast,
                                       medium (the default), slow, slower, veryslow)
    :param scale_720:  Scale to 720 pixels in height, and automatically choose width

    see more: https://askubuntu.com/questions/352920/fastest-way-to-convert-videos-batch-or-single
    '''
    if max_bitrate is None:
        max_bitrate = MAX_VIDEO_BITRATE
    if codec is None:
        codec = CODEC_BY_DEFAULT
    if preset is None:
        preset = PRESET_BY_DEFAULT

    info = get_video_info(src_file)

    # Get container info:
    format = info['format']['format_name']

    # Get video codec info:
    v_codec, v_start_time, v_bit_rate, v_pix_fmt, v_height = None, None, None, None, None
    has_b_frames = 0
    for stream in info['streams']:
        codec_type = stream['codec_type']
        if codec_type == 'video':
            v_codec = stream['codec_name'] if 'codec_name' in stream else None
            v_pix_fmt = stream['pix_fmt'] if 'pix_fmt' in stream else None
            has_b_frames = stream.get('has_b_frames', 0)
            if 'bit_rate' in stream and stream['bit_rate'] is not None:
                v_bit_rate = int(stream['bit_rate'])
            if 'start_time' in stream and stream['start_time'] is not None:
                v_start_time = float(stream['start_time'])
            if 'height' in stream and stream['height'] is not None:
                v_height = int(stream['height'])
    assert v_codec is not None, 'Video codec not found!'

    # Get audio codec info:
    a_codec = None
    for stream in info['streams']:
        codec_type = stream['codec_type']
        if codec_type == 'audio':
            a_codec = stream['codec_name'] if 'codec_name' in stream else None

    # Generate params:
    params, filters = '', ''

    # Required video filters:
    if v_pix_fmt is None or v_pix_fmt != 'yuv420p':
        filters += 'format=yuv420p'
    if fps is not None:
        filters += ',fps=' + str(fps) if len(filters) > 0 else 'fps=' + str(fps)
    if scale_720 and (v_height is None or v_height != TARGET_VIDEO_HEIGHT):
        filters += ',scale=-2:720' if len(filters) > 0 else 'scale=-2:720'
    if len(filters) > 0:
        filters = ' -vf {}'.format(filters)

    if start is not None:
        params += ' -ss {}'.format(start)
    if end is not None:
        params += ' -to {}'.format(end)

    # Re-encoding video params:
    v_only_copy = False
    if  len(filters) > 0 or start is not None or end is not None:
        params += ' -codec:v {} -bf 0'.format(codec) + filters
    elif 'h264' not in v_codec:
        params += ' -codec:v {} -bf 0'.format(codec)
    elif v_bit_rate is None or v_bit_rate > max_bitrate:
        params += ' -codec:v {} -bf 0'.format(codec)
    elif v_start_time is not None and v_start_time != 0:
        params += ' -codec:v {} -bf 0'.format(codec)
    elif has_b_frames != 0:
        params += ' -codec:v {} -bf 0'.format(codec)
    else:
        params += ' -c:v copy'
        v_only_copy = True

    # Re-encoding audio params:
    if a_codec is None:
        params += ' -an'
    else:
        params += ' -bsf:a aac_adtstoasc'

    # Encoding speed:
    if preset != 'medium':
        params += ' -preset {}'.format(preset)

    # Video encoding bitrate:
    if bitrate is not None and not v_only_copy:
        params += ' -b:v {}'.format(bitrate)

    # Run ffmpeg:
    run_ffmpeg(src_file, dst_file, params)


def sort_by_name(names):
    sorted_names = {}
    for name in names:
        base_name = name.split('__')[0]
        num = int(name.split('__')[-1].split('.')[0])
        if base_name not in sorted_names:
            sorted_names[base_name] = {}
        sorted_names[base_name][num] = name
    sorted_sorted_names = {}
    for unique, files in sorted_names.items():
        sorted_files = [files[key] for key in sorted(files.keys())]
        sorted_sorted_names[unique] = sorted_files
    return sorted_sorted_names


def main(src_folder, dst_folder, status_folder, extract_only, codec, fps,
         preset, bitrate, max_bitrate, scale_720, dst_format='.mp4', start=None, end=None, file=None):
    start_time = datetime.now()

    if file is None:
        src_files = [f for f in os.listdir(src_folder)]
    else:
        src_files = [file]

    single_src_files = src_files
    multiple_files = {} #sort_by_name([name for name in src_files if '__' in name])

    if not os.path.exists(dst_folder):
        os.makedirs(dst_folder)

    if extract_only:
        results = [os.path.join(src_folder, name) for name in src_files]
    else:
        results = []
        # convert single file games
        for name in single_src_files:
            src = os.path.join(src_folder, name)
            dst = os.path.join(dst_folder, change_ext(name, dst_format))
            dst = dst.replace('_orig', '')
            run_video_with_ffmpeg(src, dst, codec, fps, preset=preset, scale_720=scale_720,
                                  bitrate=bitrate, max_bitrate=max_bitrate, start=start, end=end)
            results.append(dst)
        # convert games recorded in multiple files
        for base_name, sources in multiple_files.items():
            sources = [os.path.join(src_folder, name) for name in sources]
            dst = os.path.join(dst_folder, base_name + dst_format)
            dst = dst.replace('_orig', '')
            run_video_concat_with_ffmpeg(sources, dst, codec, fps, preset=preset, scale_720=scale_720,
                                         bitrate=bitrate, max_bitrate=max_bitrate)
            results.append(dst)

    #  extract some frames to example the scorebug
    if status_folder is not None:
        for src_video in results:
            dst_folder = os.path.join(status_folder, get_base_name(src_video) + '_frames')
            if not os.path.exists(dst_folder):
                os.makedirs(dst_folder)
            run_extract_frames(src_video=src_video, dst_folder=dst_folder, amount_to_extract=30)
            with tarfile.open(dst_folder+'.tar', "w") as tar:
                tar.add(dst_folder, arcname=os.path.basename(dst_folder))
            shutil.rmtree(dst_folder)

    end_time = datetime.now()
    print(f'Time elapsed: {end_time - start_time}')


def parse_args():
    parser = argparse.ArgumentParser("Tool to run source video(-s) with ffmpeg based converter")
    parser.add_argument('source_video_folder',
                        help='Folder with source video(-s)')
    parser.add_argument('destination_video_folder',
                        help='Folder where to save resulting video file(-s)')
    parser.add_argument('--file', type=str, default=None,
                        help='Name of the video file to process only it')
    parser.add_argument('-b', '--bitrate', type=str, default=None,
                        help='Specific bitrate for video conversion (b=3.3M for GPU is perfect)')
    parser.add_argument('-mb', '--max_bitrate', type=int, default=MAX_VIDEO_BITRATE,
                        help='Max video bitrate above which re-encoding will be performed')
    parser.add_argument('-f', '--fps', type=int, default=None,
                        help='Target FPS')
    parser.add_argument('-p', '--preset', type=str, default='medium',
                        help='Encoding speed (see run_video_with_ffmpeg() function for details)')
    parser.add_argument('-s', '--status_folder', type=str, default=None,
                        help='Folder where to keep examples of extracted frames')
    parser.add_argument('-e', '--extract_only', action='store_true',
                        help='Just extract frames from provided videos')
    parser.add_argument('-c', '--codec', type=str, default='h264',
                        help='Codec name for converting video stream (h264 for CPU and h264_nvenc for GPU)')
    parser.add_argument('-ss', '--start', type=str, default=None,
                        help='Video start time')
    parser.add_argument('-to', '--end', type=str, default=None,
                        help='Video end time')
    feature_parser = parser.add_mutually_exclusive_group(required=False)
    feature_parser.add_argument('-s720', '--scale-720', dest='scale_720', action='store_true',
                                help='Scale to 720 pixels in height, and automatically choose width')
    feature_parser.add_argument('-no-s720', '--no-scale-720', dest='scale_720', action='store_false')
    parser.set_defaults(scale_720=False)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args.source_video_folder, args.destination_video_folder, args.status_folder, args.extract_only,
         codec=args.codec,
         fps=args.fps,
         preset=args.preset,
         bitrate=args.bitrate,
         max_bitrate=args.max_bitrate,
         scale_720=args.scale_720,
         start=args.start,
         end=args.end,
         file=args.file)
