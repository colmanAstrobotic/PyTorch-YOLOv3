# PyTorch-YOLOv3
A minimal PyTorch implementation of YOLOv3, with support for training, inference and evaluation.

## Installation
### Installing from source

For normal training and evaluation we recommend installing the package from source using a poetry virtual enviroment.

```bash
git clone https://github.com/eriklindernoren/PyTorch-YOLOv3
cd PyTorch-YOLOv3/
pip install poetry --user
poetry install
```

You need join the virtual enviroment by runing `poetry shell` in this directory before running any of the following commands without the `poetry run` prefix. Also have a look at the other installing method if you want to use the commands everywhere without opening a poetry shell.

#### Download pretrained weights

```bash
cd weights/
bash download_weights.sh
```

#### Download COCO

```bash
cd data/
bash get_coco_dataset.sh
```

### Install via pip

This installation method is less isolated and may conflict with other packages. It also only includes the code. Weights and the COCO dataset need to be installed as stated above. With this beeing said it is a good method if you want to use this package as dependency in another python project. See __API__ for further information regarding the packages api. It also enables the cli tools `yolo-detect`, `yolo-train`, and `yolo-test` everywhere without any additional commands.

```bash
pip3 install pytorchyolo --user
```

## Test
Evaluates the model on COCO test dataset.

```bash
poetry run yolo-test --weights weights/yolov3.weights
```

| Model                   | mAP (min. 50 IoU) |
| ----------------------- |:-----------------:|
| YOLOv3 608 (paper)      | 57.9              |
| YOLOv3 608 (this impl.) | 57.3              |
| YOLOv3 416 (paper)      | 55.3              |
| YOLOv3 416 (this impl.) | 55.5              |

## Inference
Uses pretrained weights to make predictions on images. Below table displays the inference times when using as inputs images scaled to 256x256. The ResNet backbone measurements are taken from the YOLOv3 paper. The Darknet-53 measurement marked shows the inference time of this implementation on my 1080ti card.

| Backbone                | GPU      | FPS      |
| ----------------------- |:--------:|:--------:|
| ResNet-101              | Titan X  | 53       |
| ResNet-152              | Titan X  | 37       |
| Darknet-53 (paper)      | Titan X  | 76       |
| Darknet-53 (this impl.) | 1080ti   | 74       |

```bash
poetry run yolo-detect --images data/samples/
```

<p align="center"><img src="https://github.com/eriklindernoren/PyTorch-YOLOv3/raw/master/assets/giraffe.png" width="480"\></p>
<p align="center"><img src="https://github.com/eriklindernoren/PyTorch-YOLOv3/raw/master/assets/dog.png" width="480"\></p>
<p align="center"><img src="https://github.com/eriklindernoren/PyTorch-YOLOv3/raw/master/assets/traffic.png" width="480"\></p>
<p align="center"><img src="https://github.com/eriklindernoren/PyTorch-YOLOv3/raw/master/assets/messi.png" width="480"\></p>

## Train
For argument descriptions have a lock at `poetry run yolo-train --help`

#### Example (COCO)
To train on COCO using a Darknet-53 backend pretrained on ImageNet run: 

```bash
poetry run yolo-train --data config/coco.data  --pretrained_weights weights/darknet53.conv.74
```

#### Tensorboard
Track training progress in Tensorboard:
* Initialize training
* Run the command below
* Go to http://localhost:6006/

```bash
poetry run tensorboard --logdir='logs' --port=6006
```

Storing the logs on a slow drive possibly leads to a significant training speed decrease.

You can adjust the log directory using `--logdir <path>` when running `tensorboard` and `yolo-train`.

## Train on Custom Dataset

#### Custom model
Run the commands below to create a custom model definition, replacing `<num-classes>` with the number of classes in your dataset.

```bash
cd config/                                # Navigate to config dir
bash create_custom_model.sh <num-classes> # Will create custom model 'yolov3-custom.cfg'
```

#### Classes
Add class names to `data/custom/classes.names`. This file should have one row per class name.

#### Image Folder
Move the images of your dataset to `data/custom/images/`.

#### Annotation Folder
Move your annotations to `data/custom/labels/`. The dataloader expects that the annotation file corresponding to the image `data/custom/images/train.jpg` has the path `data/custom/labels/train.txt`. Each row in the annotation file should define one bounding box, using the syntax `label_idx x_center y_center width height`. The coordinates should be scaled `[0, 1]`, and the `label_idx` should be zero-indexed and correspond to the row number of the class name in `data/custom/classes.names`.

#### Define Train and Validation Sets
In `data/custom/train.txt` and `data/custom/valid.txt`, add paths to images that will be used as train and validation data respectively.

#### Train
To train on the custom dataset run:

```bash
poetry run yolo-train --model config/yolov3-custom.cfg --data config/custom.data
```

Add `--pretrained_weights weights/darknet53.conv.74` to train using a backend pretrained on ImageNet.


## Credit

### YOLOv3: An Incremental Improvement
_Joseph Redmon, Ali Farhadi_ <br>

**Abstract** <br>
We present some updates to YOLO! We made a bunch
of little design changes to make it better. We also trained
this new network that’s pretty swell. It’s a little bigger than
last time but more accurate. It’s still fast though, don’t
worry. At 320 × 320 YOLOv3 runs in 22 ms at 28.2 mAP,
as accurate as SSD but three times faster. When we look
at the old .5 IOU mAP detection metric YOLOv3 is quite
good. It achieves 57.9 AP50 in 51 ms on a Titan X, compared
to 57.5 AP50 in 198 ms by RetinaNet, similar performance
but 3.8× faster. As always, all the code is online at
https://pjreddie.com/yolo/.

[[Paper]](https://pjreddie.com/media/files/papers/YOLOv3.pdf) [[Project Webpage]](https://pjreddie.com/darknet/yolo/) [[Authors' Implementation]](https://github.com/pjreddie/darknet)

```
@article{yolov3,
  title={YOLOv3: An Incremental Improvement},
  author={Redmon, Joseph and Farhadi, Ali},
  journal = {arXiv},
  year={2018}
}
```
