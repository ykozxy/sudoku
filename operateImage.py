from typing import Union

import numpy as np
from PIL import Image
from numpy.core.multiarray import ndarray

import constants


def get_image_feature(img: Image.Image):
    img = img.convert("L")
    array: ndarray = np.array(img)
    for i in range(array.shape[0]):
        for j in range(array.shape[1]):
            if array[i, j] < constants.BLACK_SENSITIVE:  # Sensible, can be changed
                array[i, j] = 1
            else:
                array[i, j] = 0
    result = resize_image_array(array)
    if result is not False:
        return calculate_feature(result)
    return False


def resize_image_array(
        array: ndarray, board_cut_tolerance: float = 0.15
) -> Union[ndarray, bool]:
    cut_up = cut_left = 0
    cut_down, cut_right = array.shape
    cut_right -= 1
    cut_down -= 1

    for i in range(int(array.shape[0] * board_cut_tolerance), -1, -1):
        if boarder_exist(array[i, :], reverse=True, min_boarder_length=0.8):
            cut_up = i
            break
    for i in range(int(array.shape[1] * board_cut_tolerance), -1, -1):
        if boarder_exist(array[:, i], reverse=True, min_boarder_length=0.8):
            cut_left = i
            break
    for i in range(
            array.shape[0] - 1, int(array.shape[0] * (1 - board_cut_tolerance) - 1), -1
    ):
        if boarder_exist(array[i, :], reverse=True, min_boarder_length=0.8):
            cut_down = i
            break
    for i in range(
            array.shape[1] - 1, int(array.shape[1] * (1 - board_cut_tolerance) - 1), -1
    ):
        if boarder_exist(array[:, i], reverse=True, min_boarder_length=0.8):
            cut_right = i
            break

    array = np.delete(array, slice(cut_down, array.shape[0]), axis=0)
    array = np.delete(array, slice(cut_right, array.shape[1]), axis=1)
    array = np.delete(array, slice(0, cut_up), axis=0)
    array = np.delete(array, slice(0, cut_left), axis=1)

    ver_slice = []
    temp = []
    for i in range(array.shape[1] - 1):
        if all(array[:, i] == 0) and any(array[:, i + 1] == 1):
            if not temp:
                temp.append(i)
            else:
                raise RuntimeError()
        elif any(array[:, i] == 1) and all(array[:, i + 1] == 0):
            if len(temp) == 1:
                temp.append(i)
                ver_slice.append(temp)
                temp = []
            else:
                raise RuntimeError
    if not ver_slice:
        return False
    ver_max = max(ver_slice, key=lambda lst: lst[1] - lst[0])
    array = np.delete(array, slice(ver_max[1] + 1, array.shape[1]), axis=1)
    array = np.delete(array, slice(0, ver_max[0] + 1), axis=1)

    # Horizontal
    hor_slice = []
    temp = []
    for i in range(array.shape[0] - 1):
        if all(array[i, :] == 0) and any(array[i + 1, :] == 1):
            if not temp:
                temp.append(i)
            else:
                raise RuntimeError()
        elif any(array[i, :] == 1) and all(array[i + 1, :] == 0):
            if len(temp) == 1:
                temp.append(i)
                hor_slice.append(temp)
                temp = []
            else:
                raise RuntimeError
    if not hor_slice:
        return False
    hor_max = max(hor_slice, key=lambda lst: lst[1] - lst[0])
    array = np.delete(array, slice(hor_max[1] + 1, array.shape[0]), axis=0)
    array = np.delete(array, slice(0, hor_max[0] + 1), axis=0)

    return array


def calculate_feature(array: ndarray):
    # assert array.shape[0] > 10 and array.shape[1] > 10
    out = []
    unit_width, unit_height = array.shape[1] // 10, array.shape[0] // 10
    for row in range(10):
        for column in range(10):
            out.append(
                array[
                    row * unit_height: (row + 1) * unit_height + 1,
                    column * unit_width: (column + 1) * unit_width + 1,
                ].mean()
            )
    out.append(array.mean())
    return out


def split_board(img: Image.Image):
    x, y = img.size
    tx, ty = x // 9, y // 9
    for q in range(9):
        for p in range(9):
            result = img.crop((tx * p, ty * q, tx * (p + 1), ty * (q + 1)))
            yield result
            # result.save(r"test\_{}{}.jpg".format(p, q))


def boarder_exist(
        array: ndarray, reverse: bool = False, min_boarder_length: float = 0.6
):
    blacks = 0
    temp_black = 0
    empty, filled = 0, 1
    if reverse:
        empty, filled = filled, empty
    for i in array:
        if i == empty:
            if temp_black > 0:
                blacks = max(blacks, temp_black)
                temp_black = 0
            else:
                temp_black = 0
                continue
        elif i == filled:
            temp_black += 1
        else:
            raise ValueError("Unexpected object type: " + i)
    blacks = max(blacks, temp_black)
    return blacks >= (len(array) * min_boarder_length)


def optimize_board(board: Image.Image, tolerance: float = 0.2):
    board = board.convert("L")
    # board.show()
    cut_up = cut_left = 0
    cut_right, cut_down = board.size
    cut_down -= 1
    cut_right -= 1
    img = np.array(board)
    for i in range(img.shape[0]):
        for j in range(img.shape[1]):
            if img[i, j] < constants.BLACK_SENSITIVE:  # Sensible, can be changed
                img[i, j] = 1
            else:
                img[i, j] = 0

    for i in range(int(img.shape[0] * tolerance), -1, -1):
        if boarder_exist(img[i, :]):
            cut_up = i
            break
    for i in range(int(img.shape[1] * tolerance), -1, -1):
        if boarder_exist(img[:, i]):
            cut_left = i
            break
    for i in range(img.shape[0] - 1, int(img.shape[0] * (1 - tolerance) - 1), -1):
        if boarder_exist(img[i, :]):
            cut_down = i
            break
    for i in range(img.shape[1] - 1, int(img.shape[1] * (1 - tolerance) - 1), -1):
        if boarder_exist(img[:, i]):
            cut_right = i
            break

    while 1:
        out = True
        if all(img[cut_up, :] == 0):
            cut_up += 1
            out = False
        if all(img[cut_down, :] == 0):
            cut_down -= 1
            out = False
        if all(img[:, cut_left] == 0):
            cut_left += 1
            out = False
        if all(img[:, cut_right] == 0):
            cut_right -= 1
            out = False
        if out:
            break

    board = board.crop((cut_left, cut_up, cut_right, cut_down))
    return board


def distance(v1: ndarray, v2: ndarray):
    return ((v1 - v2) ** 2).sum() ** 0.5


def ocr(train_set: dict, featured_image: ndarray, k=10):
    dists = [(0, 10000)]
    for num in train_set:
        for val in train_set[num]:
            dists.append((num, distance(np.array(val), featured_image)))
    dists = sorted(dists, key=lambda x: x[1])
    min_dist = {x: 0 for x in range(1, 11)}

    for dist in dists[:k]:
        min_dist[dist[0]] += 1
    return max(min_dist.keys(), key=lambda x: min_dist[x])


def main():
    get_image_feature(Image.open("debug/13.jpg"))


if __name__ == "__main__":
    main()
