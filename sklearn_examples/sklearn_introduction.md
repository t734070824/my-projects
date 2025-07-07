# Scikit-learn (sklearn) 简介

## 什么是 Scikit-learn？

Scikit-learn 是 Python 中最受欢迎的机器学习库之一，它提供了简单而高效的数据挖掘和数据分析工具。它构建在 NumPy、SciPy 和 Matplotlib 之上，提供了统一的接口来使用各种机器学习算法。

## 主要特点

### 1. 简单易用
- 一致的 API 设计
- 详细的文档和丰富的示例
- 适合初学者和专家

### 2. 功能全面
- 监督学习（分类、回归）
- 无监督学习（聚类、降维）
- 模型选择（交叉验证、网格搜索）
- 数据预处理
- 特征工程

### 3. 高效可靠
- 基于 NumPy 和 SciPy 构建
- 优化的 C 实现
- 广泛用于生产环境

## 核心模块

### 1. 监督学习 (Supervised Learning)

#### 分类 (Classification)
```python
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
```

#### 回归 (Regression)
```python
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
```

### 2. 无监督学习 (Unsupervised Learning)

#### 聚类 (Clustering)
```python
from sklearn.cluster import KMeans
from sklearn.cluster import DBSCAN
from sklearn.cluster import AgglomerativeClustering
```

#### 降维 (Dimensionality Reduction)
```python
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.decomposition import NMF
```

### 3. 数据预处理 (Data Preprocessing)
```python
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import LabelEncoder
from sklearn.impute import SimpleImputer
```

### 4. 模型选择 (Model Selection)
```python
from sklearn.model_selection import train_test_split
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import GridSearchCV
```

## 基本使用流程

### 1. 数据准备
```python
import pandas as pd
from sklearn.model_selection import train_test_split

# 加载数据
data = pd.read_csv('data.csv')
X = data.drop('target', axis=1)
y = data['target']

# 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
```

### 2. 数据预处理
```python
from sklearn.preprocessing import StandardScaler

# 标准化特征
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
```

### 3. 模型训练
```python
from sklearn.ensemble import RandomForestClassifier

# 创建模型
model = RandomForestClassifier(n_estimators=100, random_state=42)

# 训练模型
model.fit(X_train_scaled, y_train)
```

### 4. 模型评估
```python
from sklearn.metrics import accuracy_score, classification_report

# 预测
y_pred = model.predict(X_test_scaled)

# 评估
accuracy = accuracy_score(y_test, y_pred)
print(f"准确率: {accuracy:.4f}")
print(classification_report(y_test, y_pred))
```

## 常用算法示例

### 1. 线性回归
```python
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score

# 创建模型
lr = LinearRegression()

# 训练
lr.fit(X_train, y_train)

# 预测
y_pred = lr.predict(X_test)

# 评估
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)
```

### 2. 随机森林
```python
from sklearn.ensemble import RandomForestRegressor

# 创建模型
rf = RandomForestRegressor(n_estimators=100, random_state=42)

# 训练
rf.fit(X_train, y_train)

# 特征重要性
feature_importance = rf.feature_importances_
```

### 3. 支持向量机
```python
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler

# 数据标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 创建模型
svm = SVC(kernel='rbf', C=1.0)

# 训练
svm.fit(X_train_scaled, y_train)
```

## 模型选择与调优

### 1. 交叉验证
```python
from sklearn.model_selection import cross_val_score

# 5折交叉验证
scores = cross_val_score(model, X, y, cv=5)
print(f"交叉验证分数: {scores.mean():.4f} (+/- {scores.std() * 2:.4f})")
```

### 2. 网格搜索
```python
from sklearn.model_selection import GridSearchCV

# 定义参数网格
param_grid = {
    'n_estimators': [50, 100, 200],
    'max_depth': [10, 20, None],
    'min_samples_split': [2, 5, 10]
}

# 网格搜索
grid_search = GridSearchCV(RandomForestRegressor(), param_grid, cv=5)
grid_search.fit(X_train, y_train)

# 最佳参数
print(f"最佳参数: {grid_search.best_params_}")
print(f"最佳分数: {grid_search.best_score_:.4f}")
```

## 数据预处理技巧

### 1. 处理缺失值
```python
from sklearn.impute import SimpleImputer

# 数值型缺失值用均值填充
imputer = SimpleImputer(strategy='mean')
X_imputed = imputer.fit_transform(X)
```

### 2. 编码分类变量
```python
from sklearn.preprocessing import LabelEncoder, OneHotEncoder

# 标签编码
le = LabelEncoder()
y_encoded = le.fit_transform(y)

# 独热编码
ohe = OneHotEncoder(sparse=False)
X_encoded = ohe.fit_transform(X_categorical)
```

### 3. 特征缩放
```python
from sklearn.preprocessing import StandardScaler, MinMaxScaler

# 标准化 (Z-score)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 归一化 (0-1)
minmax_scaler = MinMaxScaler()
X_normalized = minmax_scaler.fit_transform(X)
```

## 实际应用场景

### 1. 房价预测
```python
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

# 训练模型
rf = RandomForestRegressor(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)

# 预测房价
predictions = rf.predict(X_test)
```

### 2. 图像分类
```python
from sklearn.svm import SVC
from sklearn.decomposition import PCA

# 降维
pca = PCA(n_components=100)
X_pca = pca.fit_transform(X)

# 分类
svm = SVC(kernel='rbf')
svm.fit(X_pca, y)
```

### 3. 客户分群
```python
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# 标准化
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 聚类
kmeans = KMeans(n_clusters=5, random_state=42)
clusters = kmeans.fit_predict(X_scaled)
```

## 最佳实践

### 1. 数据探索
- 使用 `pandas` 进行数据探索
- 检查数据质量和缺失值
- 分析特征分布和相关性

### 2. 特征工程
- 创建有意义的特征
- 处理异常值和离群点
- 选择合适的特征缩放方法

### 3. 模型选择
- 从简单模型开始
- 使用交叉验证评估性能
- 考虑模型的可解释性

### 4. 超参数调优
- 使用网格搜索或随机搜索
- 避免过拟合
- 在验证集上评估

## 总结

Scikit-learn 是 Python 机器学习的标准库，提供了：

- **完整的机器学习工具链**
- **简单一致的 API**
- **丰富的算法实现**
- **优秀的文档和社区支持**

无论是初学者还是经验丰富的数据科学家，scikit-learn 都是进行机器学习项目的首选工具。它让机器学习变得简单易用，同时保持了足够的灵活性和性能。 