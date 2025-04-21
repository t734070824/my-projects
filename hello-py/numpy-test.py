import numpy as np

x = np.array([1.0, 2.0, 3.0])
y = np.array([4.0, 5.0, 6.0])

print(x + y)

print(x - y)

print(x * y)

print(x / y)


A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])
print(A + B)

B = np.array([10, 20, 30])

# 无法广播
# print(A + B)

A = np.array([[1, 2, 4], [3, 4, 5]])
B = np.array([10, 20])
print(A + B)