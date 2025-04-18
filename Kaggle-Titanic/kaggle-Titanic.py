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

# fig = px.scatter(train_data, x='Age', y='Fare', color='Survived', hover_data=['Sex', 'Pclass'], title='Age vs Fare')
# fig.show()

#提取乘客称谓到title中
all_data['Title'] = all_data.Name.apply(lambda x: re.search(r'([A-Za-z]+)\.', x).group(1))

print(all_data['Title'].value_counts())   



# px.scatter(all_data, x="Title", y="Age", color="Sex",title="年龄、姓氏、性别分布图").show()

#整合称谓信息
all_data.loc[all_data.Title.isin(['Ms', 'Mlle']), 'Title'] = 'Miss'
all_data.loc[all_data.Title.isin(['Mme', 'Mrs']), 'Title'] = 'Mrs'
rare = ['Lady', 'Countess', 'Capt', 'Col', 'Don', 'Dr', 'Major', 'Rev', 'Sir', 'Jonkheer', 'Dona']
all_data.loc[all_data.Title.isin(rare), 'Title'] = 'Rare'
print(all_data['Title'].value_counts())   

all_data.drop(['Name'], axis=1, inplace=True)

#提取新特征
# all_data['Family_Size'] = all_data['SibSp'] + all_data['Parch'] + 1
# all_data['ticket_group_count']  = all_data.groupby('Ticket')['Ticket'].transform('count')
# all_data['group_size'] = all_data[['Family_Size', 'ticket_group_count']].max(axis=1)
# all_data['is_alone'] = all_data['group_size'].apply(lambda x: 1 if x == 1 else 0)

all_data['family_size'] = all_data.SibSp + all_data.Parch + 1
all_data['ticket_group_count'] = all_data.groupby('Ticket')['Ticket'].transform('count')
all_data['group_size'] = all_data[['family_size', 'ticket_group_count']].max(axis = 1)
all_data['is_alone'] = all_data.group_size.apply(lambda x: 1 if x == 1 else 0)


#提取新特征，并填充缺失值
all_data['fare_p'] = all_data['Fare'] / all_data.ticket_group_count
all_data.loc[all_data[all_data.fare_p.isna()].index, 'fare_p'] = all_data['fare_p'].mean()


#处理票价数据
# px.scatter(all_data, x='Pclass', y='Fare', color='Pclass', title='票价，等级分布图').show()
# fig = px.scatter(all_data, x="Pclass", y="Fare", color="Pclass",
#                  title="票价，等级分布图")
# fig.show()


all_data.drop('Fare', axis=1, inplace=True)
all_data.drop('Ticket', axis=1, inplace=True)

#分割线
print("=========================================")

print(all_data[all_data.Embarked.isnull()])
