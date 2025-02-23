from torch.utils.data import Dataset
import torch.nn.functional as F
import torch
import glob
import random
import os
import warnings
import numpy as np
from PIL import Image
from PIL import ImageFile

import sys
sys.path.append('../../AstroboticEventCameras/EventPipeline/representation/')
print(os.listdir(sys.path[-1]))
import event_reader, event_transforms

ImageFile.LOAD_TRUNCATED_IMAGES = True

def open_voxel_img(path, width, height, num_bins=3):
    aer = np.load(path)
    t = aer['t']
    x = aer['x']
    y = aer['y']
    p = aer['p']

    ed = event_reader.EventData(t, x, y, p, width, height)
    vox = event_transforms.ToVoxelGrid(num_bins)(ed)

    vox -= np.min(vox)
    vox /= np.max(vox)

    vox *= 255
    vox = vox.astype(np.uint8)

    vox = vox.transpose(1,2,0)
    return vox

def pad_to_square(img, pad_value):
    c, h, w = img.shape
    dim_diff = np.abs(h - w)
    # (upper / left) padding and (lower / right) padding
    pad1, pad2 = dim_diff // 2, dim_diff - dim_diff // 2
    # Determine padding
    pad = (0, 0, pad1, pad2) if h <= w else (pad1, pad2, 0, 0)
    # Add padding
    img = F.pad(img, pad, "constant", value=pad_value)

    return img, pad


def resize(image, size):
    image = F.interpolate(image.unsqueeze(0), size=size, mode="nearest").squeeze(0)
    return image

def resize_interp(image, size):
    image = F.interpolate(image.unsqueeze(0), size=size, mode="bilinear", align_corners=False).squeeze(0)
    return image

class VoxelFolder(Dataset):
    def __init__(self, folder_path, num_bins=3, sensor_size=(1280, 720), transform=None):
        self.files = sorted(glob.glob("%s/*.npz" % folder_path))
        self.num_bins = num_bins
        self.transform = transform
        self.width = sensor_size[0]
        self.height = sensor_size[1]

    def __getitem__(self, index):

        img_path = self.files[index % len(self.files)]
        vox = open_voxel_img(img_path, self.width, self.height, self.num_bins)

        # Label Placeholder
        boxes = np.zeros((1, 5))

        # Apply transforms
        if self.transform:
            img, _ = self.transform((vox, boxes))

        return img_path, img

    def __len__(self):
        return len(self.files)


class ImageFolder(Dataset):
    def __init__(self, folder_path, transform=None):
        self.files = sorted(glob.glob("%s/*.*" % folder_path))
        self.transform = transform

    def __getitem__(self, index):

        img_path = self.files[index % len(self.files)]
        img = np.array(
            Image.open(img_path).convert('RGB'),
            dtype=np.uint8)

        # Label Placeholder
        boxes = np.zeros((1, 5))

        # Apply transforms
        if self.transform:
            img, _ = self.transform((img, boxes))

        return img_path, img

    def __len__(self):
        return len(self.files)


class ListDataset(Dataset):
    def __init__(self, list_path, img_size=416, multiscale=True, transform=None):
        with open(list_path, "r") as file:
            self.img_files = file.readlines()

        self.label_files = []
        for path in self.img_files:
            image_dir = os.path.dirname(path)
            label_dir = "labels".join(image_dir.rsplit("images", 1))
            assert label_dir != image_dir, \
                f"Image path must contain a folder named 'images'! \n'{image_dir}'"
            label_file = os.path.join(label_dir, os.path.basename(path))
            label_file = os.path.splitext(label_file)[0] + '.txt'
            self.label_files.append(label_file)

        # self.img_files = sorted(glob.glob(os.path.join(list_path, 'images', '*.jpg')))
        # self.label_files = sorted(glob.glob(os.path.join(list_path, 'labels', '*.txt')))
        assert len(self.img_files) == len(self.label_files)

        self.img_size = img_size
        self.max_objects = 100
        self.multiscale = multiscale
        self.min_size = self.img_size - 3 * 32
        self.max_size = self.img_size + 3 * 32
        self.batch_count = 0
        self.transform = transform

    def __getitem__(self, index):

        # ---------
        #  Image
        # ---------
        try:

            img_path = self.img_files[index % len(self.img_files)].rstrip()

            img = np.array(Image.open(img_path).convert('RGB'), dtype=np.uint8)
        except Exception:
            print(f"Could not read image '{img_path}'.")
            return

        # ---------
        #  Label
        # ---------
        try:
            label_path = self.label_files[index % len(self.img_files)].rstrip()

            # Ignore warning if file is empty
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                boxes = np.loadtxt(label_path).reshape(-1, 5)
        except Exception:
            print(f"Could not read label '{label_path}'.")
            return

        # -----------
        #  Transform
        # -----------
        if self.transform:
            try:
                img, bb_targets = self.transform((img, boxes))
            except Exception:
                print("Could not apply transform.")
                return

        return img_path, img, bb_targets

    def collate_fn(self, batch):
        self.batch_count += 1

        # Drop invalid images
        batch = [data for data in batch if data is not None]

        paths, imgs, bb_targets = list(zip(*batch))

        # Selects new image size every tenth batch
        if self.multiscale and self.batch_count % 10 == 0:
            self.img_size = random.choice(
                range(self.min_size, self.max_size + 1, 32))

        # Resize images to input shape
        imgs = torch.stack([resize(img, self.img_size) for img in imgs])

        # Add sample index to targets
        for i, boxes in enumerate(bb_targets):
            boxes[:, 0] = i
        bb_targets = torch.cat(bb_targets, 0)

        return paths, imgs, bb_targets

    def __len__(self):
        return len(self.img_files)


class VoxelListDataset(Dataset):
    '''
    Yields normalized Voxel Grid tensor for input into reconstruction network.
    '''
    def __init__(self, list_path, device, img_size=416, sensor_size=(1280,720), multiscale=True, transform=None, num_bins=5):

        self.img_files = sorted(glob.glob(os.path.join(list_path, 'windows', '*.npz')))
        self.label_files = sorted(glob.glob(os.path.join(list_path, 'labels', '*.txt')))
        assert len(self.img_files) == len(self.label_files)

        self.img_size = img_size
        self.max_objects = 100
        self.multiscale = multiscale
        self.min_size = self.img_size - 3 * 32
        self.max_size = self.img_size + 3 * 32
        self.batch_count = 0
        self.transform = transform

        self.num_bins = num_bins
        self.sensor_size = sensor_size

        self.voxel_transform = event_transforms.ToVoxelGridPytorch(num_bins, device=torch.device('cpu'))
        self.voxel_norm = event_transforms.VoxelNormalize()

    def __getitem__(self, index):

        # ---------
        #  Image
        # ---------
        # try:

        img_path = self.img_files[index % len(self.img_files)].rstrip()
        npfile = np.load(img_path)
        t = npfile['t']
        x = npfile['x']
        y = npfile['y']
        p = npfile['p']
        sample = event_reader.EventData(t, x, y, p, self.sensor_size[0], self.sensor_size[1])
        sample = self.voxel_transform(sample)
        sample = self.voxel_norm(sample)
        # TODO: The image augmentation they do on this tensor requires numpy, not Tensor
        img = sample.cpu().numpy().transpose(1,2,0)

            # img = np.array(Image.open(img_path).convert('RGB'), dtype=np.uint8)

        # except Exception:
        #     print(f"Could not read image '{img_path}'.")
        #     return

        # ---------
        #  Label
        # ---------
        try:
            label_path = self.label_files[index % len(self.img_files)].rstrip()

            # Ignore warning if file is empty
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                boxes = np.loadtxt(label_path).reshape(-1, 5)
        except Exception:
            print(f"Could not read label '{label_path}'.")
            return

        # -----------
        #  Transform
        # -----------
        if self.transform:
            # try:
            img, bb_targets = self.transform((img, boxes))
            # except Exception:
                # print("Could not apply transform.")
                # return

        return img_path, img, bb_targets

    def collate_fn(self, batch):
        self.batch_count += 1

        # Drop invalid images
        batch = [data for data in batch if data is not None]

        paths, imgs, bb_targets = list(zip(*batch))

        # Selects new image size every tenth batch
        if self.multiscale and self.batch_count % 10 == 0:
            self.img_size = random.choice(
                range(self.min_size, self.max_size + 1, 32))

        # Resize images to input shape
        imgs = torch.stack([resize_interp(img, self.img_size) for img in imgs])

        # Add sample index to targets
        for i, boxes in enumerate(bb_targets):
            boxes[:, 0] = i
        bb_targets = torch.cat(bb_targets, 0)

        return paths, imgs, bb_targets

    def __len__(self):
        return len(self.img_files)