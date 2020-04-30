# yapf: disable
from keras.utils import Sequence
import numpy as np
import tensorflow as tf
import pydicom
import pandas as pd
from mask_functions import rle2mask

class DataGenerator(Sequence):

    def __init__(self, list_IDs, labels=[], batch_size=1, dim=(512,512,512), n_channels=1, n_classes=1, shuffle=True):
        self.dim = dim
        self.batch_size = batch_size
        self.labels = labels
        self.list_IDs = list_IDs
        self.n_channels = n_channels
        self.n_classes = n_classes
        self.shuffle = shuffle
        self.on_epoch_end()

        # Reading CSV file for RLEs
        self.rles = pd.read("../input/siim/train-rle.csv")

    def __len__(self):
        return int(np.floor(len(self.list_IDs) / self.batch_size))

    def __getitem__(self, index):

        indexes = self.indexes[index * self.batch_size:(index + 1) * self.batch_size]
        list_IDs_temp = [self.list_IDs[k] for k in indexes]

        X, y = self.__data_generation(list_IDs_temp)

        return X, y

    def on_epoch_end(self):

        self.indexes = np.arange(len(self.list_IDs))
        if self.shuffle:
            np.random.shuffle(self.indexes)

    def __data_generation(self, list_IDs_temp):

        # Creates an empty placeholder array that will be populated with data that is to be supplied
        X = np.empty((self.batch_size, *self.dim, self.n_channels))
        y = np.empty((self.batch_size, *self.dim, self.n_channels))

        for i, ID in enumerate(list_IDs_temp):
            # Write logic for selecting/manipulating X and y here
            img = pydicom.dcmread(ID).pixel_array
            img = np.reshape(img, (1, 1024, 1024, 1))
            img = tf.convert_to_tensor(img, dtype=tf.float16)
            ksizes = [1, 64, 64, 1]
            strides = [1, 64, 64, 1]  # how far the centres of two patches must be --> overlap area
            rates = [1, 1, 1, 1]  # dilation rate of patches
            img_patches = tf.extract_image_patches(img, ksizes, strides, rates, padding="SAME")
            
            try:
                locPD = self.rles.loc[ID.split('/')[-1][:-4], 'EncodedPixels']  # EncodedPixels data from CSV based on ID lookup
            except KeyError:
                gt = np.zeros((1024, 1024, 1))  # Assume missing masks are empty masks.

            if '-1' in locPD:
                gt = np.zeros((1024, 1024, 1))
            else:
                if type(locPD) == str:
                    gt = np.expand_dims(rle2mask(locPD, 1024, 1024), axis=2)
                else:
                    gt = np.zeros((1024, 1024, 1))
                    for x in locPD:
                        gt = gt + np.expand_dims(rle2mask(x, 1024, 1024), axis=2)
            
            print(img_patches.shape)

        return X, y