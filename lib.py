import argparse
import os
from dataclasses import dataclass, replace
from typing import List

__VERSION__ = "1.2.0"
__AUTHOR__ = "Pekka Järvinen"
__YEAR__ = 2022


class FullPaths(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, os.path.abspath(os.path.expanduser(values)))


def is_dir(dirname: str) -> str:
    if not os.path.isdir(dirname):
        msg = "'{0}' is not a directory".format(dirname)
        raise argparse.ArgumentTypeError(msg)
    else:
        return dirname


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    else:
        return False


@dataclass
class KeyFrame:
    Frame: int
    X: int
    Y: int


def get_key_frames(data: str, tuneX: int = 0, tuneY: int = 0) -> (List[KeyFrame], int, int):
    """
    Read raw motion tracking keyframe data

    Format: <frame ID>~=<start X> <start Y> <Width> <Height> <???>;next...

    :param data: Raw motion tracking keyframe data
    :param tuneX: Adjust all X
    :param tuneY: Adjust all Y
    :return:
    """

    keyframes: List[KeyFrame] = []
    xsize: int = 0
    ysize: int = 0

    for i in data.split(";"):
        key, tdata = i.split("~=")

        x, y, xs, ys, _ = map(int, tdata.split(" "))

        if xsize == 0:
            xsize = xs + abs(tuneX)
        if ysize == 0:
            ysize = ys + abs(tuneY)

        x += tuneX
        y += tuneY

        keyframes.append(KeyFrame(
            Frame=int(key),
            X=x,
            Y=y,
        ))

    return keyframes, xsize, ysize


def get_deltas(start: int, end: int, frame_count: int) -> (float, int, int, int):
    """
    Calculate how much pixels are moving
    :param start: starting coordinate
    :param end: ending coordinate
    :param frame_count: how many frames needed to move to ending position
    :return:
    """

    _max: int = max(start, end)
    _min: int = min(start, end)
    diff: int = _max - _min  # pixel count
    moving_per_frame: float = diff / frame_count  # average pixels

    if end < start:
        # moving away, turn to negative
        moving_per_frame *= -1
        diff *= -1

    return moving_per_frame, diff, _max, _min


class Smoother:
    """
    Smooth camera movement with adjustable factor (1.0 is most aggressive)
    """
    factor: float

    def __init__(self, factor: float = 0.5):
        self.set_factor(factor)

    def set_factor(self, factor: float):
        if isinstance(factor, int):
            factor = float(factor)

        if factor < 0.0:
            factor = 0.0
        elif factor > 1.0:
            factor = 1.0

        self.factor = factor

    def get_factor(self) -> float:
        return self.factor

    def smooth(self, current: int, desired: int) -> int:
        """
        Calculate smoothed camera position
        :param current:
        :param desired:
        :return:
        """

        return int(desired * self.factor + current * (1.0 - self.factor))


class Calculator:
    """
    Calculate camera movement for frames with movement smoothing
    """
    smoothX: float = 0.2  # How much smoothing for X coordinates?
    smoothY: float = 0.1  # How much smoothing for Y coordinates?

    useX: bool = True  # Use smoothing for X coordinates?
    useY: bool = False  # Use smoothing for Y coordinates?

    def __init__(self, smoothX: float = 0.2, smoothY: float = 0.1, useX: bool = True, useY: bool = False):
        self.smoothX = smoothX
        self.smoothY = smoothY
        self.useX = useX
        self.useY = useY

    def calculate(self, frames: List[KeyFrame]) -> List[KeyFrame]:
        """
        calculate missing frames with movement smoothing
        :param frames:
        :return:
        """

        # different rates for horizontal (X) and vertical (Y) movement
        smX = Smoother(self.smoothX)
        smY = Smoother(self.smoothY)

        curr_posX = frames[0].X
        curr_posY = frames[0].Y

        ret: List[KeyFrame] = []

        # Loop keyframes which might have gaps, for example 10 (0,10,20,30,40,...)
        for idx, keyF in enumerate(frames):
            try:
                endf = replace(frames[idx + 1])  # next keyframe position
                frame_count: int = 1 + (endf.Frame - keyF.Frame)  # frame count to be calculated
                # how much the picture is moving between keyframes?
                movingX, diffX, _, _ = get_deltas(keyF.X, frames[idx + 1].X, frame_count)
                movingY, diffY, _, _ = get_deltas(keyF.Y, frames[idx + 1].Y, frame_count)

                # copy new
                n = replace(keyF)
                n.X = curr_posX
                n.Y = curr_posY

                # Generate missing frames from keyframes (0-9)
                for fi in range(frame_count):
                    ret.append(replace(n))
                    n.Frame += 1

                    moveX: int = endf.X + (int(movingX) * (1 + fi))
                    moveY: int = endf.Y + (int(movingY) * (1 + fi))

                    if self.useX:
                        # Calculate smoother panning
                        curr_posX = smX.smooth(curr_posX, moveX)
                    else:
                        curr_posX += moveX

                    n.X = curr_posX

                    if self.useY:
                        # Calculate smoother panning
                        curr_posY = smY.smooth(curr_posY, moveY)
                    else:
                        curr_posY += moveY

                    n.Y = curr_posY

            except IndexError:
                continue

        return ret
