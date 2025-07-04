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

# 使用说明：
# 1. 将此代码复制到您的notebook中
# 2. 确保已经训练好xgb, lgbm, cb三个模型
# 3. 调用函数：
#    generate_weighted_submissions(test, xgb, lgbm, cb, test.index) 