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

# Sklearn - 修复版本兼容性问题
from sklearn.model_selection import train_test_split, GridSearchCV, RandomizedSearchCV, StratifiedKFold
from sklearn.metrics import (
    accuracy_score, confusion_matrix, recall_score, precision_score, f1_score,
    roc_auc_score, roc_curve
)

# 对于较新版本的 sklearn，使用以下替代方案
try:
    from sklearn.metrics import plot_confusion_matrix, plot_roc_curve
except ImportError:
    # 如果导入失败，使用替代方案
    def plot_confusion_matrix(estimator, X, y, **kwargs):
        """替代 plot_confusion_matrix 函数"""
        from sklearn.metrics import ConfusionMatrixDisplay
        y_pred = estimator.predict(X)
        cm = confusion_matrix(y, y_pred)
        disp = ConfusionMatrixDisplay(confusion_matrix=cm)
        return disp.plot(**kwargs)
    
    def plot_roc_curve(estimator, X, y, **kwargs):
        """替代 plot_roc_curve 函数"""
        from sklearn.metrics import RocCurveDisplay
        y_pred_proba = estimator.predict_proba(X)[:, 1]
        fpr, tpr, _ = roc_curve(y, y_pred_proba)
        disp = RocCurveDisplay(fpr=fpr, tpr=tpr)
        return disp.plot(**kwargs)

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

# 额外的可视化工具（替代方案）
from sklearn.metrics import ConfusionMatrixDisplay, RocCurveDisplay

print("所有导入成功完成！") 