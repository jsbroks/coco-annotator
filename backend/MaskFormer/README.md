# MaskFormer: Per-Pixel Classification is Not All You Need for Semantic Segmentation

[Bowen Cheng](https://bowenc0221.github.io/), [Alexander G. Schwing](https://alexander-schwing.de/), [Alexander Kirillov](https://alexander-kirillov.github.io/)

[[`arXiv`](http://arxiv.org/abs/2107.06278)] [[`Project`](https://bowenc0221.github.io/maskformer)] [[`BibTeX`](#CitingMaskFormer)]

<div align="center">
  <img src="https://bowenc0221.github.io/images/maskformer.png" width="100%" height="100%"/>
</div><br/>

### Features
* Better results while being more efficient.
* Unified view of semantic- and instance-level segmentation tasks.
* Support major semantic segmentation datasets: ADE20K, Cityscapes, COCO-Stuff, Mapillary Vistas.
* Support **ALL** Detectron2 models.

## Installation

See [installation instructions](INSTALL.md).

## Getting Started

See [Preparing Datasets for MaskFormer](datasets/README.md).

See [Getting Started with MaskFormer](GETTING_STARTED.md).

## Model Zoo and Baselines

We provide a large set of baseline results and trained models available for download in the [MaskFormer Model Zoo](MODEL_ZOO.md).

## License

Shield: [![CC BY-NC 4.0][cc-by-nc-shield]][cc-by-nc]

The majority of MaskFormer is licensed under a
[Creative Commons Attribution-NonCommercial 4.0 International License](LICENSE).

[![CC BY-NC 4.0][cc-by-nc-image]][cc-by-nc]

[cc-by-nc]: http://creativecommons.org/licenses/by-nc/4.0/
[cc-by-nc-image]: https://licensebuttons.net/l/by-nc/4.0/88x31.png
[cc-by-nc-shield]: https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg


However portions of the project are available under separate license terms: Swin-Transformer-Semantic-Segmentation is licensed under the [MIT license](https://github.com/SwinTransformer/Swin-Transformer-Semantic-Segmentation/blob/main/LICENSE).

## <a name="CitingMaskFormer"></a>Citing MaskFormer

If you use MaskFormer in your research or wish to refer to the baseline results published in the [Model Zoo](MODEL_ZOO.md), please use the following BibTeX entry.

```BibTeX
@article{cheng2021maskformer,
  title={Per-Pixel Classification is Not All You Need for Semantic Segmentation},
  author={Bowen Cheng and Alexander G. Schwing and Alexander Kirillov},
  journal={arXiv},
  year={2021}
}
```
