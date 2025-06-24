import warnings 
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import seaborn as sns

#设置sns样式
sns.set(style='white',context='notebook',palette='muted')
import matplotlib.pyplot as plt


train = pd.read_csv('Kaggle-Titanic-v2/train.csv')
test = pd.read_csv('Kaggle-Titanic-v2/test.csv')
print(train.head())

print(test.head())

full = pd.concat([train, test], ignore_index=True)
print(full.describe())
print(full.info())

sns.barplot(x='Embarked', y='Survived', data=train)