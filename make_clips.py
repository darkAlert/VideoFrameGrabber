import argparse
from pathlib import Path
from subprocess import check_output


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--video_path', '-v', dest='video_path', type=str, default=None,
                        help='Path to a source video file')
    parser.add_argument('--intervals_path', '-i', dest='intervals_path', type=str, default=None,
                        help='Path to an file containing time intervals in format (start,end) -> (HH:MM:SS, HH:MM:SS)')
    parser.add_argument('--output_dir', '-o', dest='output_dir', type=str, default=None,
                        help='Path to output directory where clips will be saved')
    parser.add_argument('--fast', '-f', action="store_true", default=False,
                        help='Fast making of clips, but can lead to artifacts for short clips')
    parser.add_argument('--verbose', action="store_true", default=False)

    return parser.parse_args()


def make_clip_ffmpeg(src, dst, start_time, end_time, fast=False):
    if not fast:
        cmd = f'ffmpeg -i {src} -ss {start_time} -to {end_time} -codec:v libx264 {dst} -y'
    else:
        cmd = f'ffmpeg -i {src} -ss {start_time} -to {end_time} -c copy {dst} -y'
    out = check_output(cmd.split()).decode("utf-8")

    return out


def make_clips_from_intervals(video_path, intervals_path, dst_clip_dir, fast=False, verbose=False):
    video_name = Path(video_path).stem
    (Path(dst_clip_dir) / video_name).mkdir(parents=True, exist_ok=True)  # make dst dir

    # Parse time intervals json:
    with open(intervals_path, 'r') as f:
        lines = f.read().splitlines()
    intervals = []
    for l in lines:
        t = l.replace(' ', '')
        t = t.split(',')
        intervals.append((t[0], t[1]))

    # Run ffmpeg to make clips:
    for start, end in intervals:
        dst = Path(dst_clip_dir) / video_name / '{}-{}.mp4'.format(start, end)
        print(f'Making clip {dst}')
        out = make_clip_ffmpeg(video_path, dst, start, end, fast)
        if verbose:
            print(out)

    print(f'All done! Total clips: {len(intervals)}')


if __name__ == '__main__':
    args = get_args()

    make_clips_from_intervals(
        video_path=args.video_path,
        intervals_path=args.intervals_path,
        dst_clip_dir=args.output_dir,
        fast=args.fast,
        verbose=args.verbose
    )
