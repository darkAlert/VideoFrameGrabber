import os
import argparse
import json
import datetime
import time
import subprocess
from subprocess import check_output


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--video_path', '-v', dest='video_path', type=str, default=None,
                        help='Path to source video file')
    parser.add_argument('--output_dir', '-o', dest='output_dir', type=str, default=None,
                        help='Path to output directory where frames will be saved. Can be empty')
    parser.add_argument('--start_time', '-st', dest='start_time', type=str, default='00:00:00',
                        help='Start time of video segment')
    parser.add_argument('--end_time', '-et', dest='end_time', type=str, default=None,
                        help='End time of video segment')
    parser.add_argument('--num', '-n', dest='num', type=int, default=None,
                        help='Output number of frames')
    parser.add_argument('--fps', dest='fps', type=int, default=None,
                        help='Output FPS. The argument can only be used when --num is None')
    parser.add_argument('--resolution', '-r', dest='resolution', type=str, default=None,
                        help='The resolution of output frames, e.g. 1280x720, 1920x1080')
    parser.add_argument('--quality', '-q', dest='quality', type=int, default=2,
                        help='Output frame quality in the range 1-31, where 1 is the highest and 31 is the lowest')
    parser.add_argument('--no-log', dest='log', action='store_false', default=True,
                        help="Do not save log file")
    return parser.parse_args()


def get_video_info(src, verbose=False):
    cmd = 'ffprobe -loglevel 0 -print_format json -show_format -show_streams -select_streams v:0 ' + src
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

    for p in params:
    	cmd += p.split()

    cmd += [dst]

    print(' '.join(cmd))
    subprocess.Popen(cmd).wait()

    return cmd


def timestamp_to_seconds(timestamp):
	t = time.strptime(timestamp.split(',')[0],'%H:%M:%S')
	seconds = datetime.timedelta(hours=t.tm_hour,minutes=t.tm_min,seconds=t.tm_sec).total_seconds()

	return seconds


def calc_output_fps(video_path, start_time, end_time, num):
	# Get video duration and fps:
	info = get_video_info(video_path)
	video_duration = float(info['streams'][0]['duration'])
	n,d = info['streams'][0]['avg_frame_rate'].split('/')
	video_fps = float(n) / float(d)


	# Calculate actual video duration in seconds:
	start_sec = timestamp_to_seconds(start_time)
	if end_time is not None:
		end_sec = timestamp_to_seconds(end_time)
		video_duration = end_sec if end_sec <= video_duration else video_duration
	actual_duration = video_duration - start_sec

	# Output FPS:
	fps = num / float(actual_duration)
	fps  = fps if fps <= video_fps else video_fps

	return fps


def grab(video_path, output_dir, quality, start_time='00:00:00', end_time=None, num=None, fps=None, resolution=None, log=True):
	assert video_path, '[Error] Source video path not specified!'
	assert num is None or fps is None, '[Error] The --fps argument can only be used when --num is None!'

	params = []

	# Start time:
	params.append('-ss {}'.format(start_time))

	# End time:
	if end_time is not None:
		params.append('-to {}'.format(end_time))

	# Calculate output number of frames:
	if num is not None:
		fps = calc_output_fps(video_path, start_time, end_time, num)

		# Set FPS:
		params.append('-vf fps={}'.format(fps))
	elif fps is not None:
		params.append('-vf fps={}'.format(fps))

	# Output resolution:
	if resolution is not None:
		params.append('-s {}'.format(resolution))

	# Output jpeg quality:
	assert quality >= 1 and quality <= 31, 'quality must be in the range 1-31'
	params.append('-qscale:v {}'.format(quality))

	# Output dir:
	if output_dir is None:
		filename = os.path.basename(video_path).split('.')[0]
		directory = os.path.dirname(video_path)
		output_dir = os.path.join(directory, filename)

	if not os.path.exists(output_dir):
		# shutil.rmtree(output_dir)
		os.makedirs(output_dir)
	output_path = os.path.join(output_dir, '%6d.jpeg')

	# ffmpeg:
	cmd = run_ffmpeg(video_path, output_path, params)

	# Save log:
	if log:
		log_path = os.path.join(output_dir, 'grab_log.txt')
		with open(log_path, 'w') as f:
			f.write(' '.join(cmd))

	print ('All done!')



if __name__ == '__main__':
	args = get_args()

	grab(
		video_path=args.video_path, 
		output_dir=args.output_dir,
		quality=args.quality,
		start_time=args.start_time,
		end_time=args.end_time,
		num=args.num,
		fps=args.fps,
		resolution=args.resolution,
		log=args.log
	)
