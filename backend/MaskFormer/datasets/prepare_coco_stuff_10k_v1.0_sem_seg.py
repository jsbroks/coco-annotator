#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Facebook, Inc. and its affiliates.
import os
from pathlib import Path
from shutil import copyfile

import h5py
import numpy as np
import tqdm
from PIL import Image

if __name__ == "__main__":
    dataset_dir = os.path.join(
        os.getenv("DETECTRON2_DATASETS", "datasets"), "coco", "coco_stuff_10k"
    )
    for s in ["test", "train"]:
        image_list_file = os.path.join(dataset_dir, "imageLists", f"{s}.txt")
        with open(image_list_file, "r") as f:
            image_list = f.readlines()

        image_list = [f.strip() for f in image_list]

        image_dir = os.path.join(dataset_dir, "images_detectron2", s)
        Path(image_dir).mkdir(parents=True, exist_ok=True)
        annotation_dir = os.path.join(dataset_dir, "annotations_detectron2", s)
        Path(annotation_dir).mkdir(parents=True, exist_ok=True)

        for fname in tqdm.tqdm(image_list):
            copyfile(
                os.path.join(dataset_dir, "images", fname + ".jpg"),
                os.path.join(image_dir, fname + ".jpg"),
            )

            img = np.asarray(Image.open(os.path.join(image_dir, fname + ".jpg")))

            matfile = h5py.File(os.path.join(dataset_dir, "annotations", fname + ".mat"))
            S = np.array(matfile["S"]).astype(np.uint8)
            S = np.transpose(S)
            S = S - 2  # 1 (ignore) becomes 255. others are shifted by 2

            assert S.shape == img.shape[:2], "{} vs {}".format(S.shape, img.shape)

            Image.fromarray(S).save(os.path.join(annotation_dir, fname + ".png"))
