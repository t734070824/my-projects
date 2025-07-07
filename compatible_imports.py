# Core
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
sns.set(style='darkgrid', font_scale=1.4)
from imblearn.over_sampling import SMOTE
import itertools
import warnings
warnings.filterwarnings('ignore')
import plotly.express as px
import time

# Sklearn - 兼容版本
from sklearn.model_selection import train_test_split, GridSearchCV, RandomizedSearchCV, StratifiedKFold
from sklearn.metrics import (
    accuracy_score, confusion_matrix, recall_score, precision_score, f1_score,
    roc_auc_score, roc_curve
)
from sklearn.preprocessing import StandardScaler, MinMaxScaler, OneHotEncoder, LabelEncoder
from sklearn.feature_selection import mutual_info_classif
from sklearn.decomposition import PCA
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
import eli5
from eli5.sklearn import PermutationImportance
from sklearn.utils import resample

# Models
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
from sklearn.naive_bayes import GaussianNB

# 替代可视化函数（兼容新版本 sklearn）
def plot_confusion_matrix_custom(estimator, X, y, **kwargs):
    """自定义混淆矩阵绘制函数"""
    from sklearn.metrics import ConfusionMatrixDisplay
    y_pred = estimator.predict(X)
    cm = confusion_matrix(y, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm)
    return disp.plot(**kwargs)

def plot_roc_curve_custom(estimator, X, y, **kwargs):
    """自定义ROC曲线绘制函数"""
    from sklearn.metrics import RocCurveDisplay
    y_pred_proba = estimator.predict_proba(X)[:, 1]
    fpr, tpr, _ = roc_curve(y, y_pred_proba)
    disp = RocCurveDisplay(fpr=fpr, tpr=tpr)
    return disp.plot(**kwargs)

# 设置别名以便兼容旧代码
plot_confusion_matrix = plot_confusion_matrix_custom
plot_roc_curve = plot_roc_curve_custom

print("所有导入成功完成！")
print("注意：plot_confusion_matrix 和 plot_roc_curve 已使用兼容版本替代") 