# 模型权重组合生成器

这个脚本用于生成不同权重组合的模型混合预测结果。

## 功能说明

脚本会生成所有可能的权重组合（步长为0.1），其中：
- XGBoost权重范围：0.0 到 1.0
- LightGBM权重范围：0.0 到 1.0  
- CatBoost权重范围：自动计算（确保总和为1.0）

## 使用方法

### 1. 在您的notebook中添加以下代码：

```python
import numpy as np
import pandas as pd

def blend_models_predict(X, b, c, d, xgb_model, lgbm_model, cb_model):
    """混合模型预测函数"""
    return ((b * xgb_model.predict(X)) + (c * lgbm_model.predict(X)) + (d * cb_model.predict(X)))

def generate_weighted_submissions(test, xgb_model, lgbm_model, cb_model, test_index):
    """生成不同权重组合的submission文件"""
    
    # 生成权重组合（步长0.1，总和为1）
    weights = []
    for w1 in np.arange(0.0, 1.1, 0.1):
        for w2 in np.arange(0.0, 1.1, 0.1):
            w3 = 1.0 - w1 - w2
            if 0.0 <= w3 <= 1.0:  # 确保权重在有效范围内
                weights.append((w1, w2, w3))
    
    print(f"将生成 {len(weights)} 个不同权重组合的submission文件")
    
    # 为每个权重组合生成submission
    for i, (w1, w2, w3) in enumerate(weights):
        # 确保权重总和为1（处理浮点数精度问题）
        total_weight = w1 + w2 + w3
        w1_norm = w1 / total_weight
        w2_norm = w2 / total_weight
        w3_norm = w3 / total_weight
        
        # 生成预测
        pred = blend_models_predict(test, w1_norm, w2_norm, w3_norm, xgb_model, lgbm_model, cb_model)
        pred_exp = np.exp(pred)  # 转换回原始价格尺度
        
        # 创建submission DataFrame
        submission = pd.DataFrame({
            'Id': test_index,
            'SalePrice': pred_exp
        })
        
        # 生成文件名
        filename = f"submission_{w1_norm:.1f}_{w2_norm:.1f}_{w3_norm:.1f}.csv"
        
        # 保存文件
        submission.to_csv(filename, index=False)
        
        print(f"已生成: {filename} (权重: XGBoost={w1_norm:.1f}, LightGBM={w2_norm:.1f}, CatBoost={w3_norm:.1f})")
    
    print(f"\n所有 {len(weights)} 个submission文件已生成完成！")
```

### 2. 调用函数：

```python
# 确保已经训练好模型
generate_weighted_submissions(test, xgb, lgbm, cb, test.index)
```

## 生成的文件

脚本会生成类似以下命名的文件：
- `submission_0.4_0.3_0.3.csv` (XGBoost=0.4, LightGBM=0.3, CatBoost=0.3)
- `submission_0.5_0.3_0.2.csv` (XGBoost=0.5, LightGBM=0.3, CatBoost=0.2)
- `submission_0.6_0.2_0.2.csv` (XGBoost=0.6, LightGBM=0.2, CatBoost=0.2)
- 等等...

## 权重组合数量

使用步长0.1，总共会生成约66个不同的权重组合文件。

## 注意事项

1. 确保在调用函数前已经训练好三个模型（xgb, lgbm, cb）
2. 确保test数据已经过预处理，与训练数据格式一致
3. 所有生成的CSV文件会保存在当前工作目录
4. 权重会自动归一化，确保总和为1.0

## 示例输出

```
将生成 66 个不同权重组合的submission文件
已生成: submission_0.0_0.0_1.0.csv (权重: XGBoost=0.0, LightGBM=0.0, CatBoost=1.0)
已生成: submission_0.0_0.1_0.9.csv (权重: XGBoost=0.0, LightGBM=0.1, CatBoost=0.9)
已生成: submission_0.0_0.2_0.8.csv (权重: XGBoost=0.0, LightGBM=0.2, CatBoost=0.8)
...
所有 66 个submission文件已生成完成！
``` 