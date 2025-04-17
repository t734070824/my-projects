import re
import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.impute import KNNImputer
from sklearn.cluster import KMeans
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.model_selection import cross_val_score
from hyperopt import fmin, tpe, hp, Trials
from xgboost import XGBClassifier



train_file = 'Kaggle-Titanic/train.csv'
test_file = 'Kaggle-Titanic/test.csv'

train_data = pd.read_csv(train_file)
test_data = pd.read_csv(test_file)

#合并训练、测试集数据
all_data = pd.concat([train_data, test_data], ignore_index=True)


print(train_data.head())

#分割线
print("=========================================")

print(test_data.head())

#分割线
print("=========================================")

print(all_data.info())

#分割线
print("=========================================")

print(f"训练集有{len(train_data)}条数据，测试集有{len(test_data)}条数据")
print(f"总共有{len(all_data)}条数据")

#分割线
print("=========================================")

#对样本数值数据进行更详细观察，得出其分布特征
print(round(train_data.describe(percentiles=[.5, .6, .7, .8,.9,]),2))

#分割线
print("=========================================")

print(train_data.describe(include=['O']))

#分割线
print("=========================================")

#对一些类别特征进行进一步分析，观察其与是否生存之间的相关程度
print(train_data[['Pclass', 'Survived']].groupby(['Pclass']).mean().sort_values(by='Survived', ascending=False))

#分割线
print("=========================================")
# sex 相关程序
print(train_data[['Sex', 'Survived']].groupby(['Sex']).mean().sort_values(by='Survived', ascending=False))

print(train_data[['SibSp', 'Survived']].groupby(['SibSp']).mean().sort_values(by='Survived', ascending=False))

print(train_data[['Parch','Survived']].groupby(['Parch']).mean().sort_values(by='Survived', ascending=False))

print(train_data[['Embarked', 'Survived']].groupby(['Embarked']).mean().sort_values(by='Survived', ascending=False))

#分割线
print("=========================================")

fig = px.scatter(train_data, x='Age', y='Fare', color='Survived', hover_data=['Sex', 'Pclass'], title='Age vs Fare')
fig.show()