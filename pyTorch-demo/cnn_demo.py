import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision import models
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

# 1. 加载测试图片（替换为你的图片路径）
image_path = "./cat/cat.png"  # 示例图片（建议用小猫或简单物体）
image = Image.open(image_path).convert('RGB')

# 2. 图片预处理
transform = transforms.Compose([
    transforms.Resize((224, 224)),  # 调整尺寸为CNN标准输入
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])  # ImageNet标准化
])
input_tensor = transform(image).unsqueeze(0)  # 增加batch维度

# 3. 加载预训练的CNN模型（以ResNet18为例）
model = models.resnet18(pretrained=True)
model.eval()  # 设置为评估模式

# 4. 提取第一个卷积层的权重（可视化卷积核）
first_conv_layer = model.conv1
weights = first_conv_layer.weight.detach().cpu()  # 获取权重

# 5. 可视化卷积核
plt.figure(figsize=(10, 5))
for i in range(min(16, weights.shape[0])):  # 显示前16个卷积核
    plt.subplot(4, 4, i+1)
    kernel = weights[i].permute(1, 2, 0)  # 调整维度为(H, W, C)
    # 反标准化以便显示
    kernel = (kernel - kernel.min()) / (kernel.max() - kernel.min())
    plt.imshow(kernel)
    plt.axis('off')
plt.suptitle("1-CNN的第一层卷积核(放大镜)", fontsize=14)
plt.show()

# 6. 可视化卷积后的特征图
def hook_feature(module, input, output):
    global features
    features = output.detach()

# 注册钩子获取第一个卷积层的输出
hook = first_conv_layer.register_forward_hook(hook_feature)

# 前向传播（触发钩子）
with torch.no_grad():
    model(input_tensor)

# 可视化特征图
plt.figure(figsize=(12, 6))
for i in range(min(16, features.shape[1])):  # 显示前16个特征图
    plt.subplot(4, 4, i+1)
    feature_map = features[0, i].cpu().numpy()
    plt.imshow(feature_map, cmap='viridis')  # 颜色越亮响应越强
    plt.axis('off')
plt.suptitle("2-第一层卷积后的特征图(局部特征检测)", fontsize=14)
plt.show()

# 7. 可视化深层特征（以layer4为例）
class LayerActivations:
    features = None
    def __init__(self, model, layer_num):
        self.hook = model[layer_num].register_forward_hook(self.hook_fn)
    def hook_fn(self, module, input, output):
        self.features = output.detach()
    def remove(self):
        self.hook.remove()

# 获取ResNet的第四个层输出
layer_output = LayerActivations(list(model.children())[:-2], 4)
with torch.no_grad():
    model(input_tensor)

# 随机选择部分通道可视化
deep_features = layer_output.features[0].cpu().numpy()
plt.figure(figsize=(12, 6))
for i in np.random.choice(range(deep_features.shape[0]), 16, replace=False):
    plt.subplot(4, 4, (i % 16)+1)
    plt.imshow(deep_features[i], cmap='viridis')
    plt.axis('off')
plt.suptitle("3-深层卷积特征(组合成复杂图案)", fontsize=14)
plt.show()