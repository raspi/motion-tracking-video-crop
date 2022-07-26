import argparse
import csv
import os
import subprocess
from pathlib import Path

from lib import FullPaths, is_dir, __VERSION__, __AUTHOR__, __YEAR__, str2bool

__DESCRIPTION__ = "Create cropped images from CSV data generated by gen.py with `convert` (ImageMagick)"
__EPILOG__ = "%(prog)s v{0} (c) {1} {2}-".format(__VERSION__, __AUTHOR__, __YEAR__)
__EXAMPLES__ = [
]


def convert(path: Path, width, height, startX, startY, debug=False) -> str:
    newname = Path(os.path.join(path.parent, "crop." + path.name)).absolute()

    cmd = [
        "convert",
        str(path),
    ]

    if debug:
        cmd.extend([
            "-fill", "none",
            "-stroke", "red",
            "-draw", f"rectangle {startX},{startY} {startX + width},{height}"
        ])
    else:
        cmd.extend(["-crop", f"{width}x{height}+{startX}+{startY}"])

    # output filename
    cmd.append(str(newname))

    print(" ".join(cmd))

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    if result.stderr != "":
        raise RuntimeError(result.stderr)

    if result.stdout is not None:
        return result.stdout

    return ""


def fmt(src: list) -> (int, int, int, int, int, int, int, int, str):
    for i in range(8):
        src[i] = int(src[i])

    return tuple(src)


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
        '--csv',
        default="crop.csv",
        type=str,
        dest='fname',
        required=False,
        help='CSV filename containing cropping data',
    )

    parser.add_argument(
        '--debug',
        default=False,
        type=str2bool,
        const=True,
        dest='debug',
        required=False,
        nargs='?',
        help='Enable debug mode (draws rectangles over cropping area instead of cropping)',
    )

    parser.add_argument(
        action=FullPaths,
        type=is_dir,
        dest='dir',
        help='Directory containing CSV and images',
    )

    args = parser.parse_args()

    with open(os.path.join(args.dir, args.fname), 'r', encoding='utf-8') as f:
        rdr = csv.reader(f)
        for idx, i in enumerate(rdr):
            if idx == 0:
                # First line has headers, skip
                continue

            startX, startY, endX, endY, width, height, owidth, oheight, fname = fmt(i)

            if (startX + width) > owidth:
                startX = owidth - width
            if (startY + height) > oheight:
                startY = oheight - height

            print(
                f"Processing start:X{startX:04d}Y{startY:04d} end:X{endX:04d}Y{endY:04d} {width:04d}x{height:04d} (orig: {owidth:04d}x{oheight:04d}) {fname}")
            print(convert(Path(os.path.join(args.dir, fname)).absolute(), width, height, startX, startY, args.debug))
