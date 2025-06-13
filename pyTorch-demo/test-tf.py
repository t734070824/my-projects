from PIL import Image
from torchvision import transforms
from torch.utils.tensorboard import SummaryWriter   

img_path = 'dataset/train/ants_image/0013035.jpg'
img = Image.open(img_path)
tensor_trans =   transforms.ToTensor()
tensor_img = tensor_trans(img)


writer = SummaryWriter('logs')
writer.add_image('ToTensor',tensor_img)




trans_norm = transforms.Normalize([0.5,0.5,0.5],[0.5,0.5,0.5])
trans_norm_img = trans_norm(tensor_img)
writer.add_image('Normalize',trans_norm_img, 2)



print(img.size)

trans_resize = transforms.Resize((512,512))
resize_img = trans_resize(img)
print(resize_img.size)
img_resize  = tensor_trans(resize_img)
writer.add_image('Resize',img_resize, 1)

trans_resize_2 = transforms.Resize(512)
trans_compose = transforms.Compose([trans_resize_2,tensor_trans])
img_resize_2 = trans_compose(img)
writer.add_image('Resize',img_resize_2, 2)

trans_random = transforms.RandomCrop(512,10)
trans_compose_2 = transforms.Compose([trans_random,tensor_trans])
for i in range(10):
    img_crop = trans_compose_2(img)
    print(img_crop)
    writer.add_image('RandomCrop',img_crop, i)

writer.close()