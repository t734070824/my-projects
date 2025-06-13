import os

root_dir = 'dataset/train'
target_dir = 'bees_image'

img_path = os.listdir(os.path.join(root_dir, target_dir))
label = target_dir.split('_')[0]
output_dir = 'bees_label'


for img in img_path:
    file_name = img.split('.jpg')[0]
    with open(os.path.join(root_dir, output_dir, file_name + '.txt'), 'w') as f:
        f.write(label)