# motion-tracking-video-crop

Crop video using motion tracking data from **Kdenlive** with camera *smoothing* movement.  

## Requirements

* [Python](https://www.python.org/) 3.10+
* [Kdenlive](https://kdenlive.org/en/) 22.04+
* [ffmpeg](https://ffmpeg.org/) n5.0.1+ (`ffmpeg` and `ffprobe`)
* [ImageMagick](https://imagemagick.org/) 7.1.0+ (`convert`)
* Being not afraid of terminal 

## Mini-HowTo:

First, create a folder for your project. Here we use `birb` folder because we're tracking a bird.
Copy your source video to `birb` folder as `source.mp4`.   

Open the copied video in **Kdenlive**.

Set up the *Motion Tracker* effect as per **Kdenlive** manual/tutorials tell you.

It should be as simple as adding the video to the master track 
and then drag'n'drop *Motion Tracker* from the effects to the track and 
then moving and resizing the rectangle on what you're tracking and finally clicking *Analyze*.

![Kdenlive motion tracking](_doc/kdenlive_motion_tracking.png)

When you have satisfying motion tracking data in **Kdenlive**, go to the next step.

Click on the *Copy keyframes to clipboard* on the *Motion Tracker* effect. 

It should look something like this:

```json
[
    {
        "DisplayName": "Rectangle",
        "in": 0,
        "max": 0,
        "min": 0,
        "name": "results",
        "opacity": false,
        "out": 218,
        "type": 9,
        "value": "0~=968 291 512 270 0;5~=948 295 512 270 0;10~=940 301 512 270 0;15~=930 291 512 270 0;20~=926 287 512 270 0;25~=914 291 512 270 0;30~=914 289 512 270 0;35~=928 269 512 270 0;40~=966 291 512 270 0;45~=1052 275 512 270 0;50~=1072 293 512 270 0;55~=1062 297 512 270 0;60~=1048 295 512 270 0;65~=1040 299 512 270 0;70~=1050 309 512 270 0;75~=1100 299 512 270 0;80~=1146 299 512 270 0;85~=1148 301 512 270 0;90~=1170 313 512 270 0;95~=1192 311 512 270 0;100~=1182 309 512 270 0;105~=1176 309 512 270 0;110~=1158 303 512 270 0;115~=1132 307 512 270 0;120~=1120 313 512 270 0;125~=1152 301 512 270 0;130~=1184 283 512 270 0;135~=1170 309 512 270 0;140~=1156 327 512 270 0;145~=1136 323 512 270 0;150~=1126 331 512 270 0;155~=1120 353 512 270 0;160~=1108 351 512 270 0;165~=1096 343 512 270 0;170~=1080 341 512 270 0;175~=1056 339 512 270 0;180~=1060 341 512 270 0;185~=1072 345 512 270 0;190~=1068 351 512 270 0;195~=1066 353 512 270 0;200~=1062 357 512 270 0;205~=1048 351 512 270 0;210~=1056 355 512 270 0;215~=1058 361 512 270 0;217~=1058 361 512 270 0"
    }
]
```

`[0].value` has `<keyframe number>~=X Y Width Height ?dunno?;next...` motion tracker keyframe data. 

Now create `keyframes.json` in the `birb` folder with this clipboard data.

Close **Kdenlive**.

Open terminal and go to the `birb` directory.

Extract the frames from the video:

    ffmpeg -i source.mp4 "source_%05d.png"

**`"source_%05d.png"` is hardcoded, so don't change it!**

Next we generate the cropping [CSV](https://en.wikipedia.org/wiki/Comma-separated_values) data (`crop.csv`) with smoothed movement from the `keyframes.json` file.

    python gen.py --width 600 --offsetX -50 ~/Videos/birb

Here we set `--width` manually (otherwise width from keyframe data is used automatically) to determine the final width of the video
and `--offsetX` to move all the tracking X coordinates -50 pixels.

Next we actually crop the images:

    python cropcsv.py ~/Videos/birb

This loads the `crop.csv` generated earlier and produces `crop.source_<frame>.png` images.

Then we generate the video from the images:

    ffmpeg -framerate 29.97 -i "crop.source_%05d.png" cropped.mp4

Now you have `cropped.mp4` where the moving bird is tracked.

