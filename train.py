import os
import pickle
import pprint

from operateImage import *


def train():
    train_set = {}
    for i in range(1, 10):
        features = []
        for j in os.listdir(os.getcwd() + rf"\train\{i}"):
            features.append(get_image_feature(Image.open(f"train/{i}/{j}")))
        train_set[i] = list(features)
    pprint.pprint(train_set)
    with open("train.module", "wb") as f:
        pickle.dump(train_set, f)
    return train_set


def main():
    count = 0
    for i in split_board(optimize_board(Image.open("test/sudoku10.jpg"))):
        i.save(f"debug/{count}.jpg")
        count += 1


if __name__ == "__main__":
    train()
