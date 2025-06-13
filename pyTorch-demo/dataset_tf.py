import torchvision
from torch.utils.tensorboard import SummaryWriter   

dataset_tf = torchvision.transforms.Compose([
    torchvision.transforms.ToTensor()
])


train_set = torchvision.datasets.CIFAR10(root="./dataset", train=True, transform=dataset_tf, download=True)
test_set = torchvision.datasets.CIFAR10(root="./dataset", train=False,  transform=dataset_tf,download=True)

# print(train_set[0])
# print(test_set.classes)

# img, target = train_set[0]
# print(img)
# print(target)
# print(train_set.classes[target])

# img.show()

writer = SummaryWriter('CIFAR10')
for i in range(10):
    img, target = test_set[i]
    writer.add_image('test_set',img,i)

writer.close()
