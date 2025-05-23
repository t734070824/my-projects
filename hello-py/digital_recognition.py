import sys, os
import numpy as np
import matplotlib.pyplot as plt

sys.path.append(os.pardir)

from mnist import load_mnist

from PIL import Image

def img_show(img):
    pil_img = Image.fromarray(np.uint8(img))
    pil_img.show()

(x_train, t_train), (x_test, t_test) = load_mnist(normalize=False, flatten=True)
# print(x_train.shape)
# print(t_train.shape)
# print(x_test.shape)
# print(t_test.shape)  

img = x_train[0]
label = t_train[0]

# print(label)

# print(img.shape)
# img = img.reshape(28, 28)
# print(img.shape)

# img_show(img)


def get_data():
    (x_train, t_train), (x_test, t_test) = load_mnist(normalize=False, flatten=True)
    return x_test, t_test

def init_network():
    with open("sample_weight.pkl", 'rb') as f:
        network = pickle.load(f)
    return network