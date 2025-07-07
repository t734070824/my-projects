#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scikit-learn 基本用法示例
包含分类、回归、聚类等常见机器学习任务的代码示例
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.datasets import make_classification, make_regression, make_blobs
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.svm import SVC
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    mean_squared_error, r2_score, silhouette_score
)
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def example_1_classification():
    """示例1：分类问题 - 使用逻辑回归和随机森林"""
    print("=" * 50)
    print("示例1：分类问题")
    print("=" * 50)
    
    # 生成分类数据
    X, y = make_classification(n_samples=1000, n_features=20, n_informative=15,
                             n_redundant=5, random_state=42)
    
    # 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # 数据标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 1. 逻辑回归
    print("\n1. 逻辑回归模型:")
    lr = LogisticRegression(random_state=42)
    lr.fit(X_train_scaled, y_train)
    lr_pred = lr.predict(X_test_scaled)
    lr_accuracy = accuracy_score(y_test, lr_pred)
    print(f"逻辑回归准确率: {lr_accuracy:.4f}")
    
    # 2. 随机森林
    print("\n2. 随机森林模型:")
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_train_scaled, y_train)
    rf_pred = rf.predict(X_test_scaled)
    rf_accuracy = accuracy_score(y_test, rf_pred)
    print(f"随机森林准确率: {rf_accuracy:.4f}")
    
    # 3. 支持向量机
    print("\n3. 支持向量机模型:")
    svm = SVC(kernel='rbf', random_state=42)
    svm.fit(X_train_scaled, y_train)
    svm_pred = svm.predict(X_test_scaled)
    svm_accuracy = accuracy_score(y_test, svm_pred)
    print(f"SVM准确率: {svm_accuracy:.4f}")
    
    # 模型比较
    models = ['逻辑回归', '随机森林', 'SVM']
    accuracies = [lr_accuracy, rf_accuracy, svm_accuracy]
    
    plt.figure(figsize=(10, 6))
    plt.bar(models, accuracies, color=['skyblue', 'lightgreen', 'lightcoral'])
    plt.title('不同分类模型的准确率比较')
    plt.ylabel('准确率')
    plt.ylim(0, 1)
    for i, v in enumerate(accuracies):
        plt.text(i, v + 0.01, f'{v:.4f}', ha='center', va='bottom')
    plt.tight_layout()
    plt.show()

def example_2_regression():
    """示例2：回归问题 - 房价预测"""
    print("\n" + "=" * 50)
    print("示例2：回归问题")
    print("=" * 50)
    
    # 生成回归数据
    X, y = make_regression(n_samples=1000, n_features=10, n_informative=8,
                          noise=0.1, random_state=42)
    
    # 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # 1. 线性回归
    print("\n1. 线性回归模型:")
    lr = LinearRegression()
    lr.fit(X_train, y_train)
    lr_pred = lr.predict(X_test)
    lr_mse = mean_squared_error(y_test, lr_pred)
    lr_r2 = r2_score(y_test, lr_pred)
    print(f"线性回归 MSE: {lr_mse:.4f}")
    print(f"线性回归 R²: {lr_r2:.4f}")
    
    # 2. 随机森林回归
    print("\n2. 随机森林回归模型:")
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_mse = mean_squared_error(y_test, rf_pred)
    rf_r2 = r2_score(y_test, rf_pred)
    print(f"随机森林 MSE: {rf_mse:.4f}")
    print(f"随机森林 R²: {rf_r2:.4f}")
    
    # 可视化预测结果
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    plt.scatter(y_test, lr_pred, alpha=0.5)
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
    plt.xlabel('真实值')
    plt.ylabel('预测值')
    plt.title('线性回归预测结果')
    
    plt.subplot(1, 2, 2)
    plt.scatter(y_test, rf_pred, alpha=0.5)
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
    plt.xlabel('真实值')
    plt.ylabel('预测值')
    plt.title('随机森林预测结果')
    
    plt.tight_layout()
    plt.show()

def example_3_clustering():
    """示例3：聚类问题 - K-means聚类"""
    print("\n" + "=" * 50)
    print("示例3：聚类问题")
    print("=" * 50)
    
    # 生成聚类数据
    X, y_true = make_blobs(n_samples=300, centers=4, cluster_std=0.60, random_state=42)
    
    # 数据标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # K-means聚类
    kmeans = KMeans(n_clusters=4, random_state=42)
    y_pred = kmeans.fit_predict(X_scaled)
    
    # 计算轮廓系数
    silhouette_avg = silhouette_score(X_scaled, y_pred)
    print(f"K-means聚类轮廓系数: {silhouette_avg:.4f}")
    
    # 可视化聚类结果
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    plt.scatter(X[:, 0], X[:, 1], c=y_true, cmap='viridis')
    plt.title('真实聚类')
    plt.xlabel('特征1')
    plt.ylabel('特征2')
    
    plt.subplot(1, 2, 2)
    plt.scatter(X[:, 0], X[:, 1], c=y_pred, cmap='viridis')
    plt.scatter(kmeans.cluster_centers_[:, 0], kmeans.cluster_centers_[:, 1],
                s=300, c='red', marker='x', linewidths=3, label='聚类中心')
    plt.title('K-means聚类结果')
    plt.xlabel('特征1')
    plt.ylabel('特征2')
    plt.legend()
    
    plt.tight_layout()
    plt.show()

def example_4_dimensionality_reduction():
    """示例4：降维 - PCA主成分分析"""
    print("\n" + "=" * 50)
    print("示例4：降维问题")
    print("=" * 50)
    
    # 生成高维数据
    X, y = make_classification(n_samples=1000, n_features=20, n_informative=15,
                             n_redundant=5, random_state=42)
    
    # PCA降维
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X)
    
    print(f"原始数据维度: {X.shape}")
    print(f"降维后数据维度: {X_pca.shape}")
    print(f"解释方差比例: {pca.explained_variance_ratio_}")
    print(f"累计解释方差比例: {sum(pca.explained_variance_ratio_):.4f}")
    
    # 可视化降维结果
    plt.figure(figsize=(10, 6))
    scatter = plt.scatter(X_pca[:, 0], X_pca[:, 1], c=y, cmap='viridis', alpha=0.6)
    plt.title('PCA降维结果')
    plt.xlabel('第一主成分')
    plt.ylabel('第二主成分')
    plt.colorbar(scatter)
    plt.tight_layout()
    plt.show()

def example_5_model_selection():
    """示例5：模型选择 - 交叉验证和网格搜索"""
    print("\n" + "=" * 50)
    print("示例5：模型选择")
    print("=" * 50)
    
    # 生成数据
    X, y = make_classification(n_samples=1000, n_features=20, n_informative=15,
                             n_redundant=5, random_state=42)
    
    # 数据标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 1. 交叉验证
    print("\n1. 交叉验证:")
    rf = RandomForestClassifier(random_state=42)
    cv_scores = cross_val_score(rf, X_scaled, y, cv=5)
    print(f"5折交叉验证分数: {cv_scores}")
    print(f"平均分数: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
    
    # 2. 网格搜索
    print("\n2. 网格搜索超参数调优:")
    param_grid = {
        'n_estimators': [50, 100, 200],
        'max_depth': [10, 20, None],
        'min_samples_split': [2, 5, 10]
    }
    
    grid_search = GridSearchCV(
        RandomForestClassifier(random_state=42),
        param_grid,
        cv=3,
        scoring='accuracy',
        n_jobs=-1
    )
    
    grid_search.fit(X_scaled, y)
    
    print(f"最佳参数: {grid_search.best_params_}")
    print(f"最佳交叉验证分数: {grid_search.best_score_:.4f}")
    
    # 使用最佳模型
    best_model = grid_search.best_estimator_
    print(f"最佳模型: {best_model}")

def example_6_data_preprocessing():
    """示例6：数据预处理"""
    print("\n" + "=" * 50)
    print("示例6：数据预处理")
    print("=" * 50)
    
    # 创建包含缺失值和分类变量的示例数据
    np.random.seed(42)
    n_samples = 1000
    
    # 数值特征
    feature1 = np.random.normal(0, 1, n_samples)
    feature2 = np.random.normal(0, 1, n_samples)
    
    # 添加一些缺失值
    missing_indices = np.random.choice(n_samples, size=int(n_samples * 0.1), replace=False)
    feature1[missing_indices] = np.nan
    
    # 分类特征
    categories = ['A', 'B', 'C', 'D']
    feature3 = np.random.choice(categories, n_samples)
    
    # 目标变量
    target = (feature1 + feature2 + np.random.normal(0, 0.1, n_samples) > 0).astype(int)
    
    # 创建DataFrame
    df = pd.DataFrame({
        'feature1': feature1,
        'feature2': feature2,
        'feature3': feature3,
        'target': target
    })
    
    print("原始数据:")
    print(df.head())
    print(f"\n缺失值统计:\n{df.isnull().sum()}")
    
    # 处理缺失值
    from sklearn.impute import SimpleImputer
    
    imputer = SimpleImputer(strategy='mean')
    df['feature1'] = imputer.fit_transform(df[['feature1']])
    
    print(f"\n处理缺失值后:\n{df.isnull().sum()}")
    
    # 编码分类变量
    le = LabelEncoder()
    df['feature3_encoded'] = le.fit_transform(df['feature3'])
    
    print(f"\n分类变量编码结果:")
    print(df[['feature3', 'feature3_encoded']].head(10))
    
    # 特征缩放
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(df[['feature1', 'feature2', 'feature3_encoded']])
    
    print(f"\n特征缩放后的统计信息:")
    scaled_df = pd.DataFrame(features_scaled, columns=['feature1_scaled', 'feature2_scaled', 'feature3_scaled'])
    print(scaled_df.describe())

def main():
    """主函数 - 运行所有示例"""
    print("Scikit-learn 基本用法示例")
    print("=" * 60)
    
    # 运行所有示例
    example_1_classification()
    example_2_regression()
    example_3_clustering()
    example_4_dimensionality_reduction()
    example_5_model_selection()
    example_6_data_preprocessing()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)

if __name__ == "__main__":
    main() 