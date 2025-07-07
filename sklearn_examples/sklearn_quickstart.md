# Scikit-learn 快速入门指南

## 安装

```bash
pip install scikit-learn
```

或者使用 conda：
```bash
conda install scikit-learn
```

## 5分钟快速上手

### 1. 导入必要的库
```python
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
```

### 2. 加载数据
```python
# 使用内置数据集
from sklearn.datasets import load_iris
iris = load_iris()
X = iris.data
y = iris.target

# 或者加载自己的数据
# data = pd.read_csv('your_data.csv')
# X = data.drop('target', axis=1)
# y = data['target']
```

### 3. 数据预处理
```python
# 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 数据标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
```

### 4. 训练模型
```python
# 创建模型
model = RandomForestClassifier(n_estimators=100, random_state=42)

# 训练模型
model.fit(X_train_scaled, y_train)
```

### 5. 预测和评估
```python
# 预测
y_pred = model.predict(X_test_scaled)

# 评估
accuracy = accuracy_score(y_test, y_pred)
print(f"准确率: {accuracy:.4f}")
```

## 常用算法速查表

### 分类算法
| 算法 | 导入 | 适用场景 |
|------|------|----------|
| 逻辑回归 | `from sklearn.linear_model import LogisticRegression` | 二分类，线性可分 |
| 随机森林 | `from sklearn.ensemble import RandomForestClassifier` | 多分类，特征重要 |
| SVM | `from sklearn.svm import SVC` | 小样本，非线性 |
| KNN | `from sklearn.neighbors import KNeighborsClassifier` | 简单分类，距离计算 |

### 回归算法
| 算法 | 导入 | 适用场景 |
|------|------|----------|
| 线性回归 | `from sklearn.linear_model import LinearRegression` | 线性关系 |
| 随机森林 | `from sklearn.ensemble import RandomForestRegressor` | 非线性关系 |
| SVM回归 | `from sklearn.svm import SVR` | 小样本回归 |

### 聚类算法
| 算法 | 导入 | 适用场景 |
|------|------|----------|
| K-means | `from sklearn.cluster import KMeans` | 球形聚类 |
| DBSCAN | `from sklearn.cluster import DBSCAN` | 密度聚类 |
| 层次聚类 | `from sklearn.cluster import AgglomerativeClustering` | 层次结构 |

## 数据预处理常用方法

### 处理缺失值
```python
from sklearn.impute import SimpleImputer

# 数值型用均值填充
imputer = SimpleImputer(strategy='mean')
X_imputed = imputer.fit_transform(X)

# 分类型用众数填充
imputer = SimpleImputer(strategy='most_frequent')
X_imputed = imputer.fit_transform(X)
```

### 编码分类变量
```python
from sklearn.preprocessing import LabelEncoder, OneHotEncoder

# 标签编码
le = LabelEncoder()
y_encoded = le.fit_transform(y)

# 独热编码
ohe = OneHotEncoder(sparse=False)
X_encoded = ohe.fit_transform(X_categorical)
```

### 特征缩放
```python
from sklearn.preprocessing import StandardScaler, MinMaxScaler

# 标准化 (Z-score)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 归一化 (0-1)
minmax_scaler = MinMaxScaler()
X_normalized = minmax_scaler.fit_transform(X)
```

## 模型评估指标

### 分类指标
```python
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

accuracy = accuracy_score(y_true, y_pred)
precision = precision_score(y_true, y_pred, average='weighted')
recall = recall_score(y_true, y_pred, average='weighted')
f1 = f1_score(y_true, y_pred, average='weighted')
```

### 回归指标
```python
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error

mse = mean_squared_error(y_true, y_pred)
r2 = r2_score(y_true, y_pred)
mae = mean_absolute_error(y_true, y_pred)
```

## 模型选择与调优

### 交叉验证
```python
from sklearn.model_selection import cross_val_score

scores = cross_val_score(model, X, y, cv=5)
print(f"平均分数: {scores.mean():.4f} (+/- {scores.std() * 2:.4f})")
```

### 网格搜索
```python
from sklearn.model_selection import GridSearchCV

param_grid = {
    'n_estimators': [50, 100, 200],
    'max_depth': [10, 20, None]
}

grid_search = GridSearchCV(model, param_grid, cv=5)
grid_search.fit(X, y)
print(f"最佳参数: {grid_search.best_params_}")
```

## 实用技巧

### 1. 保存和加载模型
```python
import joblib

# 保存模型
joblib.dump(model, 'model.pkl')

# 加载模型
loaded_model = joblib.load('model.pkl')
```

### 2. 特征重要性
```python
# 随机森林特征重要性
feature_importance = model.feature_importances_
feature_names = X.columns
importance_df = pd.DataFrame({
    'feature': feature_names,
    'importance': feature_importance
}).sort_values('importance', ascending=False)
```

### 3. 处理不平衡数据
```python
from imblearn.over_sampling import SMOTE

smote = SMOTE(random_state=42)
X_resampled, y_resampled = smote.fit_resample(X, y)
```

### 4. 模型解释
```python
import shap

# 创建解释器
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# 可视化
shap.summary_plot(shap_values, X_test)
```

## 常见问题解决

### 1. 过拟合
- 增加正则化参数
- 减少模型复杂度
- 使用更多训练数据
- 应用交叉验证

### 2. 欠拟合
- 增加模型复杂度
- 减少正则化
- 添加更多特征
- 使用更复杂的算法

### 3. 数据泄露
- 确保预处理步骤在训练集上进行
- 使用 Pipeline 来避免数据泄露
- 在交叉验证中正确应用预处理

## 下一步学习

1. **深入学习算法原理**
2. **掌握特征工程技巧**
3. **学习模型集成方法**
4. **了解深度学习与 sklearn 的结合**
5. **实践真实项目**

## 资源推荐

- [Scikit-learn 官方文档](https://scikit-learn.org/)
- [Scikit-learn 用户指南](https://scikit-learn.org/stable/user_guide.html)
- [Scikit-learn 示例库](https://scikit-learn.org/stable/auto_examples/)
- [机器学习实战](https://www.oreilly.com/library/view/hands-on-machine-learning/9781492032632/) 