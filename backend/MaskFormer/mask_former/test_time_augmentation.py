# Copyright (c) Facebook, Inc. and its affiliates.
import copy
from itertools import count

import numpy as np
import torch
from fvcore.transforms import HFlipTransform
from torch import nn
from torch.nn.parallel import DistributedDataParallel

from detectron2.data.detection_utils import read_image
from detectron2.modeling import DatasetMapperTTA

__all__ = [
    "SemanticSegmentorWithTTA",
]


class SemanticSegmentorWithTTA(nn.Module):
    """
    A SemanticSegmentor with test-time augmentation enabled.
    Its :meth:`__call__` method has the same interface as :meth:`SemanticSegmentor.forward`.
    """

    def __init__(self, cfg, model, tta_mapper=None, batch_size=1):
        """
        Args:
            cfg (CfgNode):
            model (SemanticSegmentor): a SemanticSegmentor to apply TTA on.
            tta_mapper (callable): takes a dataset dict and returns a list of
                augmented versions of the dataset dict. Defaults to
                `DatasetMapperTTA(cfg)`.
            batch_size (int): batch the augmented images into this batch size for inference.
        """
        super().__init__()
        if isinstance(model, DistributedDataParallel):
            model = model.module
        self.cfg = cfg.clone()

        self.model = model

        if tta_mapper is None:
            tta_mapper = DatasetMapperTTA(cfg)
        self.tta_mapper = tta_mapper
        self.batch_size = batch_size

    def _batch_inference(self, batched_inputs):
        """
        Execute inference on a list of inputs,
        using batch size = self.batch_size, instead of the length of the list.
        Inputs & outputs have the same format as :meth:`SemanticSegmentor.forward`
        """
        outputs = []
        inputs = []
        for idx, input in zip(count(), batched_inputs):
            inputs.append(input)
            if len(inputs) == self.batch_size or idx == len(batched_inputs) - 1:
                with torch.no_grad():
                    outputs.extend(self.model(inputs))
                inputs = []
        return outputs

    def __call__(self, batched_inputs):
        """
        Same input/output format as :meth:`SemanticSegmentor.forward`
        """

        def _maybe_read_image(dataset_dict):
            ret = copy.copy(dataset_dict)
            if "image" not in ret:
                image = read_image(ret.pop("file_name"), self.model.input_format)
                image = torch.from_numpy(np.ascontiguousarray(image.transpose(2, 0, 1)))  # CHW
                ret["image"] = image
            if "height" not in ret and "width" not in ret:
                ret["height"] = image.shape[1]
                ret["width"] = image.shape[2]
            return ret

        return [self._inference_one_image(_maybe_read_image(x)) for x in batched_inputs]

    def _inference_one_image(self, input):
        """
        Args:
            input (dict): one dataset dict with "image" field being a CHW tensor
        Returns:
            dict: one output dict
        """
        augmented_inputs, tfms = self._get_augmented_inputs(input)
        # 1: forward with all augmented images
        outputs = self._batch_inference(augmented_inputs)
        # Delete now useless variables to avoid being out of memory
        del augmented_inputs
        # 2: merge the results
        # handle flip specially
        new_outputs = []
        for output, tfm in zip(outputs, tfms):
            if any(isinstance(t, HFlipTransform) for t in tfm.transforms):
                new_outputs.append(output.pop("sem_seg").flip(dims=[2]))
            else:
                new_outputs.append(output.pop("sem_seg"))
        del outputs
        # to avoid OOM with torch.stack
        final_predictions = new_outputs[0]
        for i in range(1, len(new_outputs)):
            final_predictions += new_outputs[i]
        final_predictions = final_predictions / len(new_outputs)
        del new_outputs
        return {"sem_seg": final_predictions}

    def _get_augmented_inputs(self, input):
        augmented_inputs = self.tta_mapper(input)
        tfms = [x.pop("transforms") for x in augmented_inputs]
        return augmented_inputs, tfms
