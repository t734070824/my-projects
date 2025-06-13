from torch.utils.data import Dataset
from PIL import Image
import os



class Mydata(Dataset):

    def __init__(self, root_dir, label_dir):
        self.root_dir = root_dir
        self.label_dir = label_dir
        self.path = os.path.join(root_dir, label_dir)
        self.img_path = os.listdir(self.path)

    def __getitem__(self, idx):
        img_name = self.img_path[idx]
        img_item_path= os.path.join(self.root_dir, self.label_dir, img_name)
        img = Image.open(img_item_path)
        label = self.label_dir
        return img, label
    
    def __len__(self):
        return len(self.img_path)
    

root_dir = "dataset/train"
ants_bale_dir = "ants"
ants_dataset = Mydata(root_dir, ants_bale_dir)
bees_bale_dir = "bees"
bees_dataset = Mydata(root_dir, bees_bale_dir)

img, label = bees_dataset[1]

