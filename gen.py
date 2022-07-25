import argparse
import csv
import json
import os
import subprocess
import sys
from os.path import isfile
from pathlib import Path
from typing import List

from lib import KeyFrame, Calculator, is_dir, FullPaths, __VERSION__, __AUTHOR__, __YEAR__, get_key_frames

__DESCRIPTION__ = "Generate CSV file from Kdenlive motion tracking data for cropping with smoothing"
__EPILOG__ = "%(prog)s v{0} (c) {1} {2}-".format(__VERSION__, __AUTHOR__, __YEAR__)
__EXAMPLES__ = [
]


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    else:
        return False


def ffprobe(path: Path) -> dict:
    cmd = [
        "ffprobe",
        "-hide_banner",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path.absolute()),
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return json.loads(result.stdout)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__DESCRIPTION__,
        epilog=__EPILOG__,
        usage=os.linesep.join(__EXAMPLES__),
    )

    parser.add_argument(
        '--verbose', '-v',
        action='count',
        required=False,
        default=0,
        dest='verbose',
        help="Be verbose. -vvv..v Be more verbose.",
    )

    parser.add_argument(
        '--keyframes', '-f',
        default="keyframes.json",
        type=str,
        dest='file',
        required=False,
        help='File containing kdenlive motion tracking keyframes',
    )

    parser.add_argument(
        '--offsetX',
        default=0,
        type=int,
        dest='offset_x',
        required=False,
        help='Fine tune X coordinate',
    )

    parser.add_argument(
        '--offsetY',
        default=0,
        type=int,
        dest='offset_y',
        required=False,
        help='Fine tune Y coordinate',
    )

    parser.add_argument(
        '--smoothX',
        default=0.1,
        type=float,
        dest='smooth_x',
        required=False,
        help='Smoothing 0.0-1.0 for X coordinate; lower is lazy and higher more snappy',
    )

    parser.add_argument(
        '--smoothY',
        default=0.2,
        type=float,
        dest='smooth_y',
        required=False,
        help='Smoothing 0.0-1.0 for Y coordinate; lower is lazy and higher more snappy',
    )

    parser.add_argument(
        '--useY',
        default=False,
        type=str2bool,
        const=True,
        dest='use_y',
        required=False,
        nargs='?',
        help='Use Y coordinate for cropping?',
    )

    parser.add_argument(
        '--useX',
        default=True,
        type=str2bool,
        const=True,
        dest='use_x',
        required=False,
        nargs='?',
        help='Use X coordinate for cropping?',
    )

    parser.add_argument(
        '--width',
        default=0,
        type=int,
        dest='width',
        required=False,
        help='Video width, 0 fetches automatically from motion tracking data',
    )

    parser.add_argument(
        '--height',
        default=0,
        type=int,
        dest='height',
        required=False,
        help='Video height, 0 fetches automatically from motion tracking data',
    )

    parser.add_argument(
        '--csv',
        default="crop.csv",
        type=str,
        dest='outputfname',
        required=False,
        help='Output CSV filename',
    )

    parser.add_argument(
        action=FullPaths,
        type=is_dir,
        dest='dir',
        help='Directory containing files',
    )

    args = parser.parse_args()

    if args.use_x is False and args.use_y is False:
        print("You must use X or Y or both coordinates", file=sys.stderr)
        sys.exit(1)

    sizex: int = args.width  # width for end result video
    sizey: int = args.height  # height for end result video

    keyframes: List[KeyFrame] = []

    print("Loading keyframe data...")
    with open(os.path.join(args.dir, args.file), 'r', encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, list):
            data = data[0]

        if 'value' not in data:
            print("key 'value' not found", file=sys.stderr)
            sys.exit(1)

        data = data['value']

        if '~=' not in data:
            print("key 'value' doesn't seem to contain correct tracking data", file=sys.stderr)
            sys.exit(1)

        keyframes, defaultWidth, defaultHeight = get_key_frames(data, args.offset_x, args.offset_y)

        # Get default width and height for cropped video from keyframes
        if sizex == 0:
            sizex = defaultWidth
        if sizey == 0:
            sizey = defaultHeight

        del data  # don't need it anymore

    if len(keyframes) == 0:
        print("No keyframes found", file=sys.stderr)
        sys.exit(1)

    if sizex == 0:
        print("Video width is 0", file=sys.stderr)
        sys.exit(1)

    if sizey == 0:
        print("Video height is 0?", file=sys.stderr)
        sys.exit(1)

    calc = Calculator(args.smooth_x, args.smooth_y, args.use_x, args.use_y)

    # End result
    frames: List[KeyFrame] = calc.calculate(keyframes)

    # probe image size
    print("Probing image size with ffmpeg's ffprobe...")
    im = ffprobe(Path(os.path.join(args.dir, 'source_00001.png')))
    width = im['streams'][0]['width']
    height = im['streams'][0]['height']

    print("Generating CSV...")
    with open(os.path.join(args.dir, args.outputfname), 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["startX", "startY", "endX", "endY", "width", "height", "origwidth", "origheight", "file"])

        for fidx, f in enumerate(frames):
            fname = 'source_{:05d}.png'.format(fidx + 1)
            if not isfile(os.path.join(args.dir, fname)):
                continue

            startX = 0
            endX = width

            if args.use_x:
                startX = f.X
                endX = f.X + sizex

            startY = 0
            endY = height

            if args.use_y:
                startY = f.Y
                endY = f.Y + sizey

            # clip to edge
            if (startX + sizex) > width:
                startX = width - sizex
            if (startY + sizey) > height:
                startY = height - sizey

            writer.writerow([startX, startY, endX, endY, endX - startX, endY - startY, width, height, fname])

    print("Done.")