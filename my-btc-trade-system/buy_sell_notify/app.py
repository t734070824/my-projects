
import schedule
import time
import logging
import json

# 由于app.py和signal_generator.py在同一个文件夹下，可以直接导入
from signal_generator import SignalGenerator

# --- 核心分析函数 ---
def run_multi_symbol_analysis():
    """遍历多个交易对，执行多时间周期信号分析。"""
    # --- 配置区 ---
    # 如果需要代理，请在此处填入您的代理服务器地址
    PROXY = 'http://127.0.0.1:10809'  # 不需要代理则设置为 None
    
    # 要分析的交易对列表
    SYMBOLS_TO_ANALYZE = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    # ---

    for symbol in SYMBOLS_TO_ANALYZE:
        logging.info(f"================== 开始分析: {symbol} ==================")
        
        # 1. 战略层面：日线图
        logging.info(f"--- 1. [{symbol}] 分析战略层面 (日线图) ---")
        daily_signal_gen = SignalGenerator(symbol=symbol, timeframe='1d', proxy=PROXY)
        daily_analysis = daily_signal_gen.generate_signal()
        
        if daily_analysis and 'error' not in daily_analysis:
            daily_analysis_str = json.dumps(daily_analysis, indent=4, default=str, ensure_ascii=False)
            logging.info(f"[{symbol}] 日线分析结果: {daily_analysis_str}")
            
            is_long_term_bullish = daily_analysis.get('total_score', 0) > 0
            long_term_direction = "看多" if is_long_term_bullish else "看空/震荡"
            logging.info(f"[{symbol}] 长期趋势判断: {long_term_direction}")

            # 2. 战术层面：4小时图
            logging.info(f"--- 2. [{symbol}] 分析战术层面 (4小时图) ---")
            h4_signal_gen = SignalGenerator(symbol=symbol, timeframe='4h', proxy=PROXY)
            h4_analysis = h4_signal_gen.generate_signal()
            
            if h4_analysis and 'error' not in h4_analysis:
                h4_analysis_str = json.dumps(h4_analysis, indent=4, default=str, ensure_ascii=False)
                logging.info(f"[{symbol}] 4小时线分析结果: {h4_analysis_str}")
                trade_signal = h4_analysis.get('signal', 'NEUTRAL')

                # 3. 最终决策
                logging.info(f"--- 3. [{symbol}] 最终决策 ---")
                final_decision = "HOLD"
                if is_long_term_bullish and trade_signal in ['STRONG_BUY', 'WEAK_BUY']:
                    final_decision = "EXECUTE_LONG"
                    logging.warning(f"决策: {final_decision} - 原因: [{symbol}] 长期趋势看多，且短期出现买入信号。 সন")
                elif not is_long_term_bullish and trade_signal in ['STRONG_SELL', 'WEAK_SELL']:
                    final_decision = "EXECUTE_SHORT"
                    logging.warning(f"决策: {final_decision} - 原因: [{symbol}] 长期趋势看空/震荡，且短期出现卖出信号。 সন")
                else:
                    logging.info(f"决策: {final_decision} - 原因: [{symbol}] 长短期方向冲突或信号不明 ({long_term_direction} vs {trade_signal})。建议观望。 সন")
            else:
                logging.error(f"无法完成 [{symbol}] 的战术层面分析，已跳过。 সন")
        else:
            logging.error(f"无法完成 [{symbol}] 的战略层面分析，已跳过。 সন")
            
        logging.info(f"================== 完成分析: {symbol} ==================\n")

# --- 主程序入口 ---
def main():
    """主函数 - 设置定时任务"""
    logging.info("=== 新版交易信号分析系统启动 ===")
    logging.info("系统将每小时执行一次分析...")
    
    # 立即执行一次
    run_multi_symbol_analysis()
    
    # 设置定时任务：每小时执行一次分析
    schedule.every().hour.do(run_multi_symbol_analysis)
    
    # 保持程序运行
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            logging.info("\n\n系统被手动停止运行")
            break
        except Exception as e:
            logging.error(f"定时任务执行出错: {e}", exc_info=True)
            time.sleep(60)  # 出错后等待1分钟再继续

if __name__ == "__main__":
    main()
