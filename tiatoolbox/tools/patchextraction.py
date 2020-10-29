from abc import ABC
from tiatoolbox.utils.exceptions import MethodNotSupported
from tiatoolbox.utils.misc import imread

import math
import numpy as np


class PatchExtractor(ABC):
    """
    Class for extracting and merging patches in standard and whole-slide images.

    Args:
        img_patch_h(int): input image patch height.
        img_patch_w(int): input image patch width.
        pad_y(int): symmetric padding y-axis.
        pad_x(int): symmetric padding x-axis.

    """

    def __init__(self, img_patch_h, img_patch_w, pad_y, pad_x):
        self.img_patch_h = img_patch_h
        self.img_patch_w = img_patch_w
        self.pad_y = pad_y
        self.pad_x = pad_x

    def get_last_steps(self, image_dim, label_patch_dim, stride):
        """
        Get the last location for patch extraction in a specific
        direction (horizontal or vertical).

        Args:
            image_dim: 1D size of image
            label_patch_dim: 1D size of patches
            stride: 1D size of stride for patch extraction

        Returns:
            last_step: the final location for patch extraction
        """
        nr_step = math.ceil((image_dim - label_patch_dim) / stride)
        last_step = (nr_step + 1) * stride
        return int(last_step)

    def extract_patches(
        self,
        input_img_value,
        labels=None,
        save_output=False,
        save_path=None,
        save_name=None,
    ):
        """
        Extract patches from an image

        Args:
            input_img_value (str, ndarray): input image
            labels (str, ndarray):
            save_output: whether to save extracted patches
            save_path: path where saved patches will be saved (only if save_output = True)
            save_name: filename for saving patches (only if save_output = True)

        Returns:
            img_patches: extracted image patches
        """

        raise NotImplementedError

    def merge_patches(self, patches):
        """
        Merge the patch-level results to get the overall image-level prediction

        Args:
            patches: patch-level predictions

        Returns:
            image: merged prediction
        """

        raise NotImplementedError


class FixedWindowPatchExtractor(PatchExtractor):
    """Class for extracting and merging patches in standard and whole-slide images with
    fixed window size for both input image and labels.

    Args:
        img_patch_h: input image patch height
        img_patch_w: input image patch width
        stride_h: stride in horizontal direction for patch extraction
        stride_w: stride in vertical direction for patch extraction
    """

    def __init__(self, img_patch_h, img_patch_w, stride_h=1, stride_w=1):
        super(PatchExtractor, self).__init__(
            img_patch_h=img_patch_h, img_patch_w=img_patch_w
        )
        self.stride_h = stride_h
        self.stride_w = stride_w

        raise NotImplementedError


class VariableWindowPatchExtractor(PatchExtractor):
    """Class for extracting and merging patches in standard and whole-slide images with
    variable window size for both input image and labels.

    Args:
        img_patch_h: input image patch height
        img_patch_w: input image patch width
        stride_h: stride in horizontal direction for patch extraction
        stride_w: stride in vertical direction for patch extraction
        label_patch_h: network output label height
        label_patch_w: network output label width
    """

    def __init__(
        self,
        img_patch_h,
        img_patch_w,
        stride_h=1,
        stride_w=1,
        label_patch_h=None,
        label_patch_w=None,
    ):
        super(PatchExtractor, self).__init__(
            img_patch_h=img_patch_h, img_patch_w=img_patch_w
        )
        self.stride_h = stride_h
        self.stride_w = stride_w
        self.label_patch_h = label_patch_h
        self.label_patch_w = label_patch_w

        raise NotImplementedError


class PointsPatchExtractor(PatchExtractor):
    """
    Class for extracting patches in standard and whole-slide images with specified point
    as a centre.

    Args:
        img_patch_h: input image patch height
        img_patch_w: input image patch width
    """

    def __init__(self, img_patch_h, img_patch_w, pad_y, pad_x, input_points, num_examples_per_patch=9  # Square Root of Num of Examples must be odd
    ):
        super(PatchExtractor, self).__init__(
            img_patch_h=img_patch_h, img_patch_w=img_patch_w, pad_y=pad_y, pad_x=pad_x
        )
        self.input_points = input_points
        self.num_examples_per_patch=num_examples_per_patch

    def extract_patches(
        self, input_img, labels=None, save_output=False, save_path=None, save_name=None
    ):
        if isinstance(self.input_points, np.ndarray):
            input_points = self.input_points
        else:
            raise Exception("Please input correct csv, json path or csv data")

        if type(input_img) == str:
            image = imread(input_img)
        elif isinstance(input_img, np.ndarray):
            image = input_img
        else:
            raise Exception("Please input correct image path or numpy array")

        patch_h = self.img_patch_h
        patch_w = self.img_patch_w

        image = np.lib.pad(
            image,
            ((self.pad_y, self.pad_y), (self.pad_x, self.pad_x), (0, 0)),
            "symmetric",
        )

        num_patches_img = len(input_points) * self.num_examples_per_patch
        img_patches = np.zeros(
            (num_patches_img, patch_h, patch_w, image.shape[2]), dtype=image.dtype
        )
        labels = []
        cell_id = []
        for i in range(num_patches_img):
            labels.append([])
            cell_id.append([])

        img_h = np.size(image, 0)
        img_w = np.size(image, 1)
        img_d = np.size(image, 2)

        cell_tot = 1
        iter_tot = 0
        for row in input_points:
            cell_type = row[0]
            cell_location = np.array([row[2], row[1]], dtype=np.int)
            cell_location[0] = (
                cell_location[0] + self.pad_y - 1
            )  # Python index starts from 0
            cell_location[1] = (
                cell_location[1] + self.pad_x - 1
            )  # Python index starts from 0
            if self.num_examples_per_patch > 1:
                root_num_examples = np.sqrt(self.num_examples_per_patch)
                start_location = -int(root_num_examples / 2)
                end_location = int(root_num_examples + start_location)
            else:
                start_location = 0
                end_location = 1

            for h in range(start_location, end_location):
                for w in range(start_location, end_location):
                    start_h = cell_location[0] - h - int((patch_h - 1) / 2)
                    start_w = cell_location[1] - w - int((patch_w - 1) / 2)
                    end_h = start_h + patch_h
                    end_w = start_w + patch_w
                    labels[iter_tot] = cell_type
                    cell_id[iter_tot] = cell_tot
                    img_patches[iter_tot, :, :, :] = image[start_h:end_h, start_w:end_w]
                    iter_tot += 1

            cell_tot += 1
        return img_patches, labels, cell_id

    def merge_patches(self, patches=None):
        raise MethodNotSupported(
            message="Merge patches not supported for " "PointsPatchExtractor"
        )


def get_patch_extractor(
    method_name, img_patch_h=224, img_patch_w=224, input_points=None, pad_y=0, pad_x=0
):
    """Return a patch extractor object as requested.
    Args:
        method_name (str): name of patch extraction method, must be one of
                            "point", "fixedwindow", "variablwindow".
        img_patch_h(int): desired image patch height, default=224.
        img_patch_w(int): desired image patch width, default=224.
        input_points(pd.dataframe, pathlib.Path): pandas dataframe with x, y, l,
          columns or path to csv/json containing input points and labels for patch
          extraction using points defined by x, y and l(labels).
        pad_y(int): symmetric padding y-axis, default=0.
        pad_x(int): symmetric padding x-axis, default=0.
    Return:
        PatchExtractor : an object with base 'PatchExtractor' as base class.
    Examples:
        >>> from tiatoolbox.tools.patchextraction import get_patch_extractor
        >>> # PointsPatchExtractor with default values
        >>> patch_extract = get_patch_extractor('point')

    """
    if method_name.lower() == "point":
        patch_extractor = PointsPatchExtractor(
            img_patch_h=img_patch_h,
            img_patch_w=img_patch_w,
            pad_y=pad_y,
            pad_x=pad_x,
            input_points=input_points,
        )
    elif method_name.lower() == "fixedwindow":
        patch_extractor = FixedWindowPatchExtractor(
            img_patch_h=img_patch_h, img_patch_w=img_patch_w
        )
    elif method_name.lower() == "variablewindow":
        patch_extractor = VariableWindowPatchExtractor(
            img_patch_h=img_patch_h, img_patch_w=img_patch_w
        )
    else:
        raise MethodNotSupported

    return patch_extractor