from pipeline import (
    PipelineRunner,
    ContourDetection,
    Visualizer,
    CsvWriter,
    VehicleCounter)
import os
import logging
import logging.handlers
import random

import numpy as np
import cv2
import matplotlib.pyplot as plt

import utils
random.seed(123)


# ============================================================================
IMAGE_DIR = "./out"
VIDEO_SOURCE = "waterdale_long.mp4"
VIDEO_OUT_DEST = "output_waterdale_long.mp4"
# SHAPE = (360, 640)
# EXIT_PTS = np.array([
#     [[366, 360], [366, 250], [640, 250], [640, 360]],
#     [[0, 200], [322, 200], [322, 0], [0, 0]]
# ])
EXIT_PTS = np.array([
    [[0, 240], [320, 240], [320, 180], [0, 180]]
]) # 320*240
MIN_CONTOUR_RATIO = 35./720
# ============================================================================


def train_bg_subtractor(inst, cap, num=500):
    '''
        BG substractor need process some amount of frames to start giving result
    '''
    print('Training BG Subtractor...')
    i = 0
    while(cap.isOpened()):
        ret, frame = cap.read()
        if ret == True:
            inst.apply(frame, None, 0.001)
            i += 1
            if i >= num:
                break
        else:
            break


def main():
    log = logging.getLogger("main")

    # Set up image source
    cap = cv2.VideoCapture(VIDEO_SOURCE)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(width,height)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(VIDEO_OUT_DEST, fourcc, fps, (width, height))

    # creating exit mask from points, where we will be counting our vehicles
    base = np.zeros((height, width) + (3,), dtype='uint8')
    exit_mask = cv2.fillPoly(base, EXIT_PTS, (255, 255, 255))[:, :, 0]

    # there is also bgslibrary, that seems to give better BG substruction, but
    # not tested it yet
    bg_subtractor = cv2.createBackgroundSubtractorMOG2(
        history=500, detectShadows=True)

    # processing pipline for programming conviniance
    pipeline = PipelineRunner(pipeline=[
        ContourDetection(bg_subtractor=bg_subtractor,
                         min_contour_width=int(MIN_CONTOUR_RATIO*height),
                         min_contour_height=int(MIN_CONTOUR_RATIO*height),
                         save_image=False, image_dir=IMAGE_DIR),
        # we use y_weight == 2.0 because traffic are moving vertically on video
        # use x_weight == 2.0 for horizontal.
        VehicleCounter(exit_masks=[exit_mask], y_weight=2.0),
        Visualizer(video_out=out, image_dir=IMAGE_DIR, save_image=False),
        CsvWriter(path='./', name='report.csv')
    ], log_level=logging.DEBUG)

    # skipping 500 frames to train bg subtractor, close video and reopen
    train_bg_subtractor(bg_subtractor, cap, num=500)
    cap.release()

    _frame_number = -1
    frame_number = -1
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    while(cap.isOpened()):
        ret, frame = cap.read()
        if ret == True:
            # real frame number
            _frame_number += 1

            # # skip every 2nd frame to speed up processing
            # if _frame_number % 2 != 0:
            #     continue

            # frame number that will be passed to pipline
            # this needed to make video from cutted frames
            frame_number += 1

            # plt.imshow(frame)
            # plt.show()
            # return

            pipeline.set_context({
                'frame': frame,
                'frame_number': frame_number,
            })
            pipeline.run()

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            break
    # Release everything if job is finished
    cap.release()
    out.release()
    cv2.destroyAllWindows()

# ============================================================================


if __name__ == "__main__":
    log = utils.init_logging()

    if not os.path.exists(IMAGE_DIR):
        log.debug("Creating image directory `%s`...", IMAGE_DIR)
        os.makedirs(IMAGE_DIR)

    main()
