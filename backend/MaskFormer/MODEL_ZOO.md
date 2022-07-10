# MaskFormer Model Zoo and Baselines

## Introduction

This file documents a collection of models reported in our paper.
All numbers were obtained on [Big Basin](https://engineering.fb.com/data-center-engineering/introducing-big-basin-our-next-generation-ai-hardware/)
servers with 8 NVIDIA V100 GPUs & NVLink (except COCO panoptic segmentation models are trained with 64 NVIDIA V100 GPUs).

#### How to Read the Tables
* The "Name" column contains a link to the config file. Running `train_net.py --num-gpus 8` with this config file
  will reproduce the model (except for COCO panoptic segmentation models are trained with 64 NVIDIA V100 GPUs with distributed training).
* The *model id* column is provided for ease of reference.
  To check downloaded file integrity, any model on this page contains its md5 prefix in its file name.
* Training curves and other statistics can be found in `metrics` for each model.

#### Detectron2 ImageNet Pretrained Models

It's common to initialize from backbone models pre-trained on ImageNet classification tasks. The following backbone models are available:

* [R-50.pkl (torchvision)](https://dl.fbaipublicfiles.com/detectron2/ImageNetPretrained/torchvision/R-50.pkl): converted copy of [torchvision's ResNet-50](https://pytorch.org/docs/stable/torchvision/models.html#torchvision.models.resnet50) model.
  More details can be found in [the conversion script](tools/convert-torchvision-to-d2.py).
* [R-103.pkl](https://dl.fbaipublicfiles.com/detectron2/DeepLab/R-103.pkl): a ResNet-101 with its first 7x7 convolution replaced by 3 3x3 convolutions. This modification has been used in most semantic segmentation papers (a.k.a. ResNet101c in our paper). We pre-train this backbone on ImageNet using the default recipe of [pytorch examples](https://github.com/pytorch/examples/tree/master/imagenet).

Note: below are available pretrained models in Detectron2 that we do not use in our paper.
* [R-50.pkl](https://dl.fbaipublicfiles.com/detectron2/ImageNetPretrained/MSRA/R-50.pkl): converted copy of [MSRA's original ResNet-50](https://github.com/KaimingHe/deep-residual-networks) model.
* [R-101.pkl](https://dl.fbaipublicfiles.com/detectron2/ImageNetPretrained/MSRA/R-101.pkl): converted copy of [MSRA's original ResNet-101](https://github.com/KaimingHe/deep-residual-networks) model.
* [X-101-32x8d.pkl](https://dl.fbaipublicfiles.com/detectron2/ImageNetPretrained/FAIR/X-101-32x8d.pkl): ResNeXt-101-32x8d model trained with Caffe2 at FB.

#### Third-party ImageNet Pretrained Models

Our paper also uses ImageNet pretrained models that are not part of Detectron2, please refer to [tools](https://github.com/facebookresearch/MaskFormer/tree/master/tools) to get those pretrained models.

#### License

All models available for download through this document are licensed under the
[Creative Commons Attribution-NonCommercial 4.0 International License](https://creativecommons.org/licenses/by-nc/4.0/).

### Semantic Segmentation Models

#### ADE20K Semantic Segmentation

<table><tbody>
<!-- START TABLE -->
<!-- TABLE HEADER -->
<th valign="bottom">Name</th>
<th valign="bottom">Backbone</th>
<th valign="bottom">crop<br/>size</th>
<th valign="bottom">lr<br/>sched</th>
<th valign="bottom">train<br/>mem<br/>(MB)</th>
<th valign="bottom">mIoU</th>
<th valign="bottom">mIoU<br/>(ms+flip)</th>
<th valign="bottom">model id</th>
<th valign="bottom">download</th>
<!-- TABLE BODY -->
<!-- ROW: per_pixel_baseline_R50_bs16_160k -->
 <tr><td align="left"><a href="configs/ade20k-150/per_pixel_baseline_R50_bs16_160k.yaml">PerPixelBaseline</a></td>
<td align="center">R50</td>
<td align="center">512x512</td>
<td align="center">160k</td>
<td align="center">2451</td>
<td align="center">39.2</td>
<td align="center">40.9</td>
<td align="center">40913338_1</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/per_pixel_baseline_R50_bs16_160k/model_final_1043f3.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/per_pixel_baseline_R50_bs16_160k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: per_pixel_baseline_plus_R50_bs16_160k -->
 <tr><td align="left"><a href="configs/ade20k-150/per_pixel_baseline_plus_R50_bs16_160k.yaml">PerPixelBaseline+</a></td>
<td align="center">R50</td>
<td align="center">512x512</td>
<td align="center">160k</td>
<td align="center">5817</td>
<td align="center">41.9</td>
<td align="center">42.9</td>
<td align="center">40931736_2</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/per_pixel_baseline_plus_R50_bs16_160k/model_final_833630.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/per_pixel_baseline_plus_R50_bs16_160k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_R50_bs16_160k -->
 <tr><td align="left"><a href="configs/ade20k-150/maskformer_R50_bs16_160k.yaml">MaskFormer</a></td>
<td align="center">R50</td>
<td align="center">512x512</td>
<td align="center">160k</td>
<td align="center">4334</td>
<td align="center">44.5</td>
<td align="center">46.7</td>
<td align="center">40931736_14</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/maskformer_R50_bs16_160k/model_final_d8dbeb.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/maskformer_R50_bs16_160k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_R101_bs16_160k -->
 <tr><td align="left"><a href="configs/ade20k-150/maskformer_R101_bs16_160k.yaml">MaskFormer</a></td>
<td align="center">R101</td>
<td align="center">512x512</td>
<td align="center">160k</td>
<td align="center">4905</td>
<td align="center">45.5</td>
<td align="center">47.2</td>
<td align="center">40986936_1</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/maskformer_R101_bs16_160k/model_final_1aeb94.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/maskformer_R101_bs16_160k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_R101c_bs16_160k -->
 <tr><td align="left"><a href="configs/ade20k-150/maskformer_R101c_bs16_160k.yaml">MaskFormer</a></td>
<td align="center">R101c</td>
<td align="center">512x512</td>
<td align="center">160k</td>
<td align="center">4968</td>
<td align="center">46.0</td>
<td align="center">48.1</td>
<td align="center">41703904_1</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/maskformer_R101c_bs16_160k/model_final_b432ea.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/maskformer_R101c_bs16_160k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_swin_tiny_bs16_160k -->
 <tr><td align="left"><a href="configs/ade20k-150/swin/maskformer_swin_tiny_bs16_160k.yaml">MaskFormer</a></td>
<td align="center">Swin-T</td>
<td align="center">512x512</td>
<td align="center">160k</td>
<td align="center">5292</td>
<td align="center">46.7</td>
<td align="center">48.8</td>
<td align="center">40986951_3</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/maskformer_swin_tiny_bs16_160k/model_final_8657a5.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/maskformer_swin_tiny_bs16_160k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_swin_small_bs16_160k -->
 <tr><td align="left"><a href="configs/ade20k-150/swin/maskformer_swin_small_bs16_160k.yaml">MaskFormer</a></td>
<td align="center">Swin-S</td>
<td align="center">512x512</td>
<td align="center">160k</td>
<td align="center">6330</td>
<td align="center">49.8</td>
<td align="center">51.0</td>
<td align="center">40846700_5</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/maskformer_swin_small_bs16_160k/model_final_528157.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/maskformer_swin_small_bs16_160k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_swin_base_IN21k_384_bs16_160k_res640 -->
 <tr><td align="left"><a href="configs/ade20k-150/swin/maskformer_swin_base_IN21k_384_bs16_160k_res640.yaml">MaskFormer</a></td>
<td align="center">Swin-B</td>
<td align="center">640x640</td>
<td align="center">160k</td>
<td align="center">12928</td>
<td align="center">52.7</td>
<td align="center">53.9</td>
<td align="center">40986951_0</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/maskformer_swin_base_IN21k_384_bs16_160k_res640/model_final_45388b.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/maskformer_swin_base_IN21k_384_bs16_160k_res640/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_swin_large_IN21k_384_bs16_160k_res640 -->
 <tr><td align="left"><a href="configs/ade20k-150/swin/maskformer_swin_large_IN21k_384_bs16_160k_res640.yaml">MaskFormer</a></td>
<td align="center">Swin-L</td>
<td align="center">640x640</td>
<td align="center">160k</td>
<td align="center">18144</td>
<td align="center">54.1</td>
<td align="center">55.6</td>
<td align="center">40846700_0</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/maskformer_swin_large_IN21k_384_bs16_160k_res640/model_final_aefa3b.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k/maskformer_swin_large_IN21k_384_bs16_160k_res640/metrics.json">metrics</a></td>
</tr>
</tbody></table>

#### COCO-Stuff-10K Semantic Segmentation

<table><tbody>
<!-- START TABLE -->
<!-- TABLE HEADER -->
<th valign="bottom">Name</th>
<th valign="bottom">Backbone</th>
<th valign="bottom">lr<br/>sched</th>
<th valign="bottom">train<br/>mem<br/>(MB)</th>
<th valign="bottom">mIoU</th>
<th valign="bottom">mIoU<br/>(ms+flip)</th>
<th valign="bottom">model id</th>
<th valign="bottom">download</th>
<!-- TABLE BODY -->
<!-- ROW: per_pixel_baseline_R50_bs32_60k -->
 <tr><td align="left"><a href="configs/coco-stuff-10k-171/per_pixel_baseline_R50_bs32_60k.yaml">PerPixelBaseline</a></td>
<td align="center">R50</td>
<td align="center">60k</td>
<td align="center">6898</td>
<td align="center">32.4</td>
<td align="center">34.4</td>
<td align="center">40941321_0</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-coco-stuff-10k/per_pixel_baseline_R50_bs32_60k/model_final_275ab0.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-coco-stuff-10k/per_pixel_baseline_R50_bs32_60k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: per_pixel_baseline_plus_R50_bs32_60k -->
 <tr><td align="left"><a href="configs/coco-stuff-10k-171/per_pixel_baseline_plus_R50_bs32_60k.yaml">PerPixelBaseline+</a></td>
<td align="center">R50</td>
<td align="center">60k</td>
<td align="center">18227</td>
<td align="center">34.2</td>
<td align="center">35.8</td>
<td align="center">40941321_3</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-coco-stuff-10k/per_pixel_baseline_plus_R50_bs32_60k/model_final_1fa920.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-coco-stuff-10k/per_pixel_baseline_plus_R50_bs32_60k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_R50_bs32_60k -->
 <tr><td align="left"><a href="configs/coco-stuff-10k-171/maskformer_R50_bs32_60k.yaml">MaskFormer</a></td>
<td align="center">R50</td>
<td align="center">60k</td>
<td align="center">8618</td>
<td align="center">37.1</td>
<td align="center">38.9</td>
<td align="center">40941321_6</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-coco-stuff-10k/maskformer_R50_bs32_60k/model_final_cb03eb.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-coco-stuff-10k/maskformer_R50_bs32_60k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_R101_bs32_60k -->
 <tr><td align="left"><a href="configs/coco-stuff-10k-171/maskformer_R101_bs32_60k.yaml">MaskFormer</a></td>
<td align="center">R101</td>
<td align="center">60k</td>
<td align="center">10091</td>
<td align="center">38.1</td>
<td align="center">39.8</td>
<td align="center">40986940_1</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-coco-stuff-10k/maskformer_R101_bs32_60k/model_final_eb19bb.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-coco-stuff-10k/maskformer_R101_bs32_60k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_R101c_bs32_60k -->
 <tr><td align="left"><a href="configs/coco-stuff-10k-171/maskformer_R101c_bs32_60k.yaml">MaskFormer</a></td>
<td align="center">R101c</td>
<td align="center">60k</td>
<td align="center">9927</td>
<td align="center">38.0</td>
<td align="center">39.3</td>
<td align="center">41703904_3</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-coco-stuff-10k/maskformer_R101c_bs32_60k/model_final_bffd25.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-coco-stuff-10k/maskformer_R101c_bs32_60k/metrics.json">metrics</a></td>
</tr>
</tbody></table>

#### ADE20K-Full Semantic Segmentation

<table><tbody>
<!-- START TABLE -->
<!-- TABLE HEADER -->
<th valign="bottom">Name</th>
<th valign="bottom">Backbone</th>
<th valign="bottom">lr<br/>sched</th>
<th valign="bottom">train<br/>mem<br/>(MB)</th>
<th valign="bottom">mIoU</th>
<th valign="bottom">model id</th>
<th valign="bottom">download</th>
<!-- TABLE BODY -->
<!-- ROW: per_pixel_baseline_R50_bs16_200k -->
 <tr><td align="left"><a href="configs/ade20k-full-847/per_pixel_baseline_R50_bs16_200k.yaml">PerPixelBaseline</a></td>
<td align="center">R50</td>
<td align="center">200k</td>
<td align="center">8030</td>
<td align="center">12.4</td>
<td align="center">40986914_5</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k-full/per_pixel_baseline_R50_bs16_200k/model_final_9f66a9.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k-full/per_pixel_baseline_R50_bs16_200k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: per_pixel_baseline_plus_R50_bs16_200k -->
 <tr><td align="left"><a href="configs/ade20k-full-847/per_pixel_baseline_plus_R50_bs16_200k.yaml">PerPixelBaseline+</a></td>
<td align="center">R50</td>
<td align="center">200k</td>
<td align="center">26698</td>
<td align="center">13.9</td>
<td align="center">40986914_6</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k-full/per_pixel_baseline_plus_R50_bs16_200k/model_final_4d31f2.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k-full/per_pixel_baseline_plus_R50_bs16_200k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_R50_bs16_200k -->
 <tr><td align="left"><a href="configs/ade20k-full-847/maskformer_R50_bs16_200k.yaml">MaskFormer</a></td>
<td align="center">R50</td>
<td align="center">200k</td>
<td align="center">6529</td>
<td align="center">16.0</td>
<td align="center">40986914_1</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k-full/maskformer_R50_bs16_200k/model_final_f4e3f6.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k-full/maskformer_R50_bs16_200k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_R101_bs16_200k -->
 <tr><td align="left"><a href="configs/ade20k-full-847/maskformer_R101_bs16_200k.yaml">MaskFormer</a></td>
<td align="center">R101</td>
<td align="center">200k</td>
<td align="center">6894</td>
<td align="center">16.8</td>
<td align="center">40986946_1</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k-full/maskformer_R101_bs16_200k/model_final_88df33.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k-full/maskformer_R101_bs16_200k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_R101c_bs16_200k -->
 <tr><td align="left"><a href="configs/ade20k-full-847/maskformer_R101c_bs16_200k.yaml">MaskFormer</a></td>
<td align="center">R101c</td>
<td align="center">200k</td>
<td align="center">6904</td>
<td align="center">17.4</td>
<td align="center">41703904_6</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k-full/maskformer_R101c_bs16_200k/model_final_75d34e.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-ade20k-full/maskformer_R101c_bs16_200k/metrics.json">metrics</a></td>
</tr>
</tbody></table>

#### Cityscapes Semantic Segmentation

<table><tbody>
<!-- START TABLE -->
<!-- TABLE HEADER -->
<th valign="bottom">Name</th>
<th valign="bottom">Backbone</th>
<th valign="bottom">lr<br/>sched</th>
<th valign="bottom">train<br/>mem<br/>(MB)</th>
<th valign="bottom">mIoU</th>
<th valign="bottom">mIoU<br/>(ms+flip)</th>
<th valign="bottom">model id</th>
<th valign="bottom">download</th>
<!-- TABLE BODY -->
<!-- ROW: maskformer_R101_bs16_90k -->
 <tr><td align="left"><a href="configs/cityscapes-19/maskformer_R101_bs16_90k.yaml">MaskFormer</a></td>
<td align="center">R101</td>
<td align="center">90k</td>
<td align="center">6960</td>
<td align="center">78.5</td>
<td align="center">80.3</td>
<td align="center">41127351_1</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-cityscapes/maskformer_R101_bs16_90k/model_final_38c00c.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-cityscapes/maskformer_R101_bs16_90k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_R101c_bs16_90k -->
 <tr><td align="left"><a href="configs/cityscapes-19/maskformer_R101c_bs16_90k.yaml">MaskFormer</a></td>
<td align="center">R101c</td>
<td align="center">90k</td>
<td align="center">7204</td>
<td align="center">79.7</td>
<td align="center">81.4</td>
<td align="center">41630444_2</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-cityscapes/maskformer_R101c_bs16_90k/model_final_4f8ff9.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-cityscapes/maskformer_R101c_bs16_90k/metrics.json">metrics</a></td>
</tr>
</tbody></table>

#### Mapillary Vistas Semantic Segmentation

<table><tbody>
<!-- START TABLE -->
<!-- TABLE HEADER -->
<th valign="bottom">Name</th>
<th valign="bottom">Backbone</th>
<th valign="bottom">lr<br/>sched</th>
<th valign="bottom">train<br/>mem<br/>(MB)</th>
<th valign="bottom">mIoU</th>
<th valign="bottom">mIoU<br/>(ms+flip)</th>
<th valign="bottom">model id</th>
<th valign="bottom">download</th>
<!-- TABLE BODY -->
<!-- ROW: maskformer_R50_bs16_300k -->
 <tr><td align="left"><a href="configs/mapillary-vistas-65/maskformer_R50_bs16_300k.yaml">MaskFormer</a></td>
<td align="center">R50</td>
<td align="center">300k</td>
<td align="center">15761</td>
<td align="center">53.1</td>
<td align="center">55.4</td>
<td align="center">42325118</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/semantic-mapillary-vistas/maskformer_R50_bs16_300k/model_final_f3fc73.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/semantic-mapillary-vistas/maskformer_R50_bs16_300k/metrics.json">metrics</a></td>
</tr>
</tbody></table>

### Panoptic Segmentation Models

#### COCO Panoptic Segmentation

<table><tbody>
<!-- START TABLE -->
<!-- TABLE HEADER -->
<th valign="bottom">Name</th>
<th valign="bottom">Backbone</th>
<th valign="bottom">lr<br/>sched</th>
<th valign="bottom">train<br/>mem<br/>(MB)</th>
<th valign="bottom">PQ</th>
<th valign="bottom">model id</th>
<th valign="bottom">download</th>
<!-- TABLE BODY -->
<!-- ROW: maskformer_panoptic_R50_bs64_554k -->
 <tr><td align="left"><a href="configs/coco-panoptic/maskformer_panoptic_R50_bs64_554k.yaml">MaskFormer</a></td>
<td align="center">R50 + 6 Enc</td>
<td align="center">554k</td>
<td align="center">22634</td>
<td align="center">46.5</td>
<td align="center">42747488_1</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/panoptic-coco/maskformer_panoptic_R50_bs64_554k/model_final_6f60dc.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/panoptic-coco/maskformer_panoptic_R50_bs64_554k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_panoptic_R101_bs64_554k -->
 <tr><td align="left"><a href="configs/coco-panoptic/maskformer_panoptic_R101_bs64_554k.yaml">MaskFormer</a></td>
<td align="center">R101 + 6 Enc</td>
<td align="center">554k</td>
<td align="center">27358</td>
<td align="center">47.6</td>
<td align="center">42747488_0</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/panoptic-coco/maskformer_panoptic_R101_bs64_554k/model_final_57b049.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/panoptic-coco/maskformer_panoptic_R101_bs64_554k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_panoptic_swin_tiny_bs64_554k -->
 <tr><td align="left"><a href="configs/coco-panoptic/swin/maskformer_panoptic_swin_tiny_bs64_554k.yaml">MaskFormer</a></td>
<td align="center">Swin-T</td>
<td align="center">554k</td>
<td align="center">20023</td>
<td align="center">47.7</td>
<td align="center">41143190_0</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/panoptic-coco/maskformer_panoptic_swin_tiny_bs64_554k/model_final_539394.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/panoptic-coco/maskformer_panoptic_swin_tiny_bs64_554k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_panoptic_swin_small_bs64_554k -->
 <tr><td align="left"><a href="configs/coco-panoptic/swin/maskformer_panoptic_swin_small_bs64_554k.yaml">MaskFormer</a></td>
<td align="center">Swin-S</td>
<td align="center">554k</td>
<td align="center">21620</td>
<td align="center">49.7</td>
<td align="center">41270920</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/panoptic-coco/maskformer_panoptic_swin_small_bs64_554k/model_final_5bf6b1.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/panoptic-coco/maskformer_panoptic_swin_small_bs64_554k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_panoptic_swin_base_IN21k_384_bs64_554k -->
 <tr><td align="left"><a href="configs/coco-panoptic/swin/maskformer_panoptic_swin_base_IN21k_384_bs64_554k.yaml">MaskFormer</a></td>
<td align="center">Swin-B</td>
<td align="center">554k</td>
<td align="center">24411</td>
<td align="center">51.8</td>
<td align="center">41260906</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/panoptic-coco/maskformer_panoptic_swin_base_IN21k_384_bs64_554k/model_final_4b7f49.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/panoptic-coco/maskformer_panoptic_swin_base_IN21k_384_bs64_554k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_panoptic_swin_large_IN21k_384_bs64_554k -->
 <tr><td align="left"><a href="configs/coco-panoptic/swin/maskformer_panoptic_swin_large_IN21k_384_bs64_554k.yaml">MaskFormer</a></td>
<td align="center">Swin-L</td>
<td align="center">554k</td>
<td align="center">23275</td>
<td align="center">52.7</td>
<td align="center">43219274</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/panoptic-coco/maskformer_panoptic_swin_large_IN21k_384_bs64_554k/model_final_7505c4.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/panoptic-coco/maskformer_panoptic_swin_large_IN21k_384_bs64_554k/metrics.json">metrics</a></td>
</tr>
</tbody></table>

Note:
* All COCO panoptic segmentation models are trained with 64 NVIDIA V100 GPUs.
* For Swin-L model, we set `MAX_SIZE_TRAIN=1000` due to memory constraint.

#### ADE20K Panoptic Segmentation

<table><tbody>
<!-- START TABLE -->
<!-- TABLE HEADER -->
<th valign="bottom">Name</th>
<th valign="bottom">Backbone</th>
<th valign="bottom">lr<br/>sched</th>
<th valign="bottom">train<br/>mem<br/>(MB)</th>
<th valign="bottom">PQ</th>
<th valign="bottom">model id</th>
<th valign="bottom">download</th>
<!-- TABLE BODY -->
<!-- ROW: maskformer_panoptic_R50_bs16_720k -->
 <tr><td align="left"><a href="configs/ade20k-150-panoptic/maskformer_panoptic_R50_bs16_720k.yaml">MaskFormer</a></td>
<td align="center">R50 + 6 Enc</td>
<td align="center">720k</td>
<td align="center">15899</td>
<td align="center">34.7</td>
<td align="center">42746872_1</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/panoptic-ade20k/maskformer_panoptic_R50_bs16_720k/model_final_7aa977.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/panoptic-ade20k/maskformer_panoptic_R50_bs16_720k/metrics.json">metrics</a></td>
</tr>
<!-- ROW: maskformer_panoptic_R101_bs16_720k -->
 <tr><td align="left"><a href="configs/ade20k-150-panoptic/maskformer_panoptic_R101_bs16_720k.yaml">MaskFormer</a></td>
<td align="center">R50 + 6 Enc</td>
<td align="center">720k</td>
<td align="center">16516</td>
<td align="center">35.7</td>
<td align="center">42747444</td>
<td align="center"><a href="https://dl.fbaipublicfiles.com/maskformer/panoptic-ade20k/maskformer_panoptic_R101_bs16_720k/model_final_0b3cc8.pkl">model</a>&nbsp;|&nbsp;<a href="https://dl.fbaipublicfiles.com/maskformer/panoptic-ade20k/maskformer_panoptic_R101_bs16_720k/metrics.json">metrics</a></td>
</tr>
</tbody></table>
