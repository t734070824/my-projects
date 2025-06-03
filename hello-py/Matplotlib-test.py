import numpy as np
import matplotlib.pyplot as plt

x = np.arange(0, 100, 0.1)
y = np.sin(x)

# plt.plot(x, y)
# plt.title('Sine Wave')
# plt.xlabel('X-axis')
# plt.ylabel('Y-axis')
# plt.grid(True)
# plt.show()

def AND(x1, x2):
    x = np.array([x1, x2])
    w = np.array([0.5, 0.5])
    b = -0.7
    tmp = np.sum(w * x) + b
    if tmp <= 0:
        return 0
    else:
        return 1
    

def NAND(x1, x2):
    x = np.array([x1, x2])
    w = np.array([-0.5, -0.5])
    b = 0.7
    tmp = np.sum(w * x) + b
    if tmp <= 0:
        return 0
    else:
        return 1
    
def OR(x1, x2):
    x = np.array([x1, x2])
    w = np.array([0.5, 0.5])
    b = -0.2
    tmp = np.sum(w * x) + b
    if tmp <= 0:
        return 0
    else:
        return 1
    
def XOR(x1, x2):
    s1 = NAND(x1, x2)
    s2 = OR(x1, x2)
    y = AND(s1, s2)
    return y

def step_function(x):
    return np.array(x > 0, dtype=int)





print(AND(0, 0))  # 0
print(AND(1, 0))  # 0
print(AND(0, 1))  # 0
print(AND(1, 1))  # 1

x = np.arange(-50.0, 50.0, 0.1)
y = step_function(x)
# plt.plot(x, y)
# plt.ylim(-0.1, 1.1)
# plt.show()


def sigmoid(x):
    return 1 / (1 + np.exp(-x))

x = np.arange(-5.0, 5.0, 0.1)
y = sigmoid(x)
# print(y)
# plt.plot(x, y)
# plt.ylim(-0.1, 1.1)
# plt.show()

def relu(x):
    return np.maximum(0, x)


X = np.array([1.0, 0.5])
W1 = np.array([[0.1, 0.3, 0.5], 
              [0.2, 0.4, 0.6]])
B1 = np.array([0.1, 0.2, 0.3])

A1 = np.dot(X, W1) + B1
print(A1)
Z1 = sigmoid(A1)
print(Z1)

W2 = np.array([[0.1, 0.4],
              [0.2, 0.5],
              [0.3, 0.6]])
B2 = np.array([0.1, 0.2])

A2 = np.dot(Z1, W2) + B2
print(A2)
Z2 = sigmoid(A2)
print(Z2)

# 分割线
print("=========================================")


def identity_function(x):
    return x

def init_network():
    network = {}
    network['W1'] = np.array([[0.1, 0.3, 0.5], 
                               [0.2, 0.4, 0.6]])
    network['b1'] = np.array([0.1, 0.2, 0.3])

    network['W2'] = np.array([[0.1, 0.4],
                               [0.2, 0.5],
                               [0.3, 0.6]])
    network['b2'] = np.array([0.1, 0.2])

    network['W3'] = np.array([[0.1, 0.3],
                               [0.2, 0.4]])
    network['b3'] = np.array([0.1, 0.2])
    return network

def forward(network, x):
    W1, W2, W3 = network['W1'], network['W2'], network['W3']
    b1, b2, b3 = network['b1'], network['b2'], network['b3']

    A1 = np.dot(x, W1) + b1
    Z1 = sigmoid(A1)

    A2 = np.dot(Z1, W2) + b2
    Z2 = sigmoid(A2)

    A3 = np.dot(Z2, W3) + b3
    Y = identity_function(A3)

    return Y

network = init_network()
x = np.array([1.0, 0.5])
y = forward(network, x)
print(y)

# 分割线
print("=========================================")

def softmax(a):
    c = np.max(a)
    exp_a = np.exp(a - c)  # overflow
    sum_exp_a = np.sum(exp_a)
    y = exp_a / sum_exp_a
    return y


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

def predict(network, x):
    W1, W2, W3 = network['W1'], network['W2'], network['W3']
    b1, b2, b3 = network['b1'], network['b2'], network['b3']

    a1 = np.dot(x, W1) + b1
    z1 = sigmoid(a1)
    a2 = np.dot(z1, W2) + b2
    z2 = sigmoid(a2)
    a3 = np.dot(z2, W3) + b3
    y = softmax(a3)

    return y