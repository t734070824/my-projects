# coding: utf-8
import numpy as np


def identity_function(x):
    return x


def step_function(x):
    return np.array(x > 0, dtype=int)


def sigmoid(x):
    """处理数值溢出的优化版sigmoid函数"""
    # 对于非常大的负值，直接返回0，避免exp溢出
    mask = x < 0
    result = np.ones_like(x)
    
    # 对于负值，使用 exp(x)/(1+exp(x)) 形式计算
    exp_x = np.exp(x[mask])
    result[mask] = exp_x / (1 + exp_x)
    
    # 对于非负值，使用标准形式
    exp_neg_x = np.exp(-x[~mask])
    result[~mask] = 1 / (1 + exp_neg_x)
    
    return result

def sigmoid_grad(x):
    return (1.0 - sigmoid(x)) * sigmoid(x)


def relu(x):
    return np.maximum(0, x)


def relu_grad(x):
    grad = np.zeros_like(x)
    grad[x>=0] = 1
    return grad


def softmax(x):
    x = x - np.max(x, axis=-1, keepdims=True)   # オーバーフロー対策
    return np.exp(x) / np.sum(np.exp(x), axis=-1, keepdims=True)


def sum_squared_error(y, t):
    return 0.5 * np.sum((y-t)**2)


def cross_entropy_error(y, t):
    if y.ndim == 1:
        t = t.reshape(1, t.size)
        y = y.reshape(1, y.size)

    # 教師データがone-hot-vectorの場合、正解ラベルのインデックスに変換
    if t.size == y.size:
        t = t.argmax(axis=1)

    batch_size = y.shape[0]
    return -np.sum(np.log(y[np.arange(batch_size), t] + 1e-7)) / batch_size


def softmax_loss(X, t):
    y = softmax(X)
    return cross_entropy_error(y, t)