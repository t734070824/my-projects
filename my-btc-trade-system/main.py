import requests
import json
from datetime import datetime
import pandas as pd
import time
import logging
import ssl
from config import (
    BINANCE_API_CONFIG, 
    DATA_FETCH_CONFIG, 
    RISK_ANALYSIS_CONFIG,
    LOGGING_CONFIG,
    OUTPUT_CONFIG
)

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format'],
    handlers=[
        logging.FileHandler(LOGGING_CONFIG['file']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BinanceDataFetcher:
    """币安数据获取器"""
    
    def __init__(self):
        self.base_url = BINANCE_API_CONFIG['base_url']
        self.timeout = BINANCE_API_CONFIG['timeout']
        self.retry_times = DATA_FETCH_CONFIG['retry_times']
        self.retry_delay = DATA_FETCH_CONFIG['retry_delay']
        
        # 创建session以复用连接
        self.session = requests.Session()
        
        # 配置SSL和代理设置
        self._configure_session()
        
    def _configure_session(self):
        """配置session的SSL和代理设置"""
        # SSL验证设置
        self.session.verify = DATA_FETCH_CONFIG['enable_ssl_verify']
        
        # 设置用户代理
        self.session.headers.update({
            'User-Agent': DATA_FETCH_CONFIG['user_agent']
        })
        
        # 代理设置
        if DATA_FETCH_CONFIG['enable_proxy']:
            self.session.proxies = DATA_FETCH_CONFIG['proxy_settings']
        else:
            self.session.proxies = {}
        
    def get_klines(self, symbol=None, interval=None, limit=None):
        """
        获取K线数据
        
        Args:
            symbol: 交易对，默认使用配置文件中的设置
            interval: 时间间隔，默认使用配置文件中的设置
            limit: 获取数量，默认使用配置文件中的设置
            
        Returns:
            DataFrame: 包含K线数据的DataFrame
        """
        # 使用配置文件中的默认值
        symbol = symbol or BINANCE_API_CONFIG['default_symbol']
        interval = interval or BINANCE_API_CONFIG['default_interval']
        limit = limit or BINANCE_API_CONFIG['default_limit']
        
        for attempt in range(self.retry_times):
            try:
                params = {
                    'symbol': symbol,
                    'interval': interval,
                    'limit': limit
                }
                
                logger.info(f"正在获取 {symbol} {interval} K线数据，第 {attempt + 1} 次尝试")
                
                # 使用session进行请求
                response = self.session.get(
                    self.base_url, 
                    params=params, 
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                
                # 转换为DataFrame
                df = pd.DataFrame(data, columns=[
                    'open_time', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_asset_volume', 'number_of_trades',
                    'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                ])
                
                # 转换数据类型
                numeric_columns = ['open', 'high', 'low', 'close', 'volume', 
                                 'quote_asset_volume', 'number_of_trades',
                                 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
                
                for col in numeric_columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # 转换时间戳并添加+8小时时区
                df['open_time'] = pd.to_datetime(df['open_time'], unit='ms') + pd.Timedelta(hours=8)
                df['close_time'] = pd.to_datetime(df['close_time'], unit='ms') + pd.Timedelta(hours=8)
                
                logger.info(f"成功获取 {len(df)} 条K线数据")
                return df
                
            except requests.exceptions.SSLError as e:
                logger.error(f"SSL连接错误 (尝试 {attempt + 1}/{self.retry_times}): {e}")
                if attempt < self.retry_times - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error("SSL连接失败，尝试使用备用方法")
                    return self._get_klines_fallback(symbol, interval, limit)
                    
            except requests.exceptions.ProxyError as e:
                logger.error(f"代理连接错误 (尝试 {attempt + 1}/{self.retry_times}): {e}")
                # 禁用代理重试
                self.session.proxies = {}
                if attempt < self.retry_times - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error("代理连接失败")
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"网络请求失败 (尝试 {attempt + 1}/{self.retry_times}): {e}")
                if attempt < self.retry_times - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error("所有重试都失败了")
                    return None
            except Exception as e:
                logger.error(f"处理数据时出错: {e}")
                return None
    
    def _get_klines_fallback(self, symbol, interval, limit):
        """备用数据获取方法"""
        try:
            logger.info("使用备用方法获取数据...")
            
            # 使用更简单的请求设置
            session = requests.Session()
            session.verify = False
            session.proxies = {}
            
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = session.get(
                self.base_url, 
                params=params, 
                timeout=60  # 增加超时时间
            )
            response.raise_for_status()
            
            data = response.json()
            
            # 转换为DataFrame
            df = pd.DataFrame(data, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 转换数据类型
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 
                             'quote_asset_volume', 'number_of_trades',
                             'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
            
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 转换时间戳并添加+8小时时区
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms') + pd.Timedelta(hours=8)
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms') + pd.Timedelta(hours=8)
            
            logger.info(f"备用方法成功获取 {len(df)} 条K线数据")
            return df
            
        except Exception as e:
            logger.error(f"备用方法也失败了: {e}")
            return None

class DataAnalyzer:
    """数据分析器"""
    
    def __init__(self):
        self.config = RISK_ANALYSIS_CONFIG
        
    def calculate_indicators(self, df):
        """计算技术指标"""
        if df is None or len(df) == 0:
            return df
            
        # 计算移动平均线
        for period in self.config['ma_periods']:
            if len(df) >= period:
                df[f'ma_{period}'] = df['close'].rolling(window=period).mean()
        
        # 计算价格变化率
        df['price_change'] = df['close'].pct_change()
        df['price_change_pct'] = df['price_change'] * 100
        
        # 计算成交量变化率
        df['volume_change'] = df['volume'].pct_change()
        df['volume_change_pct'] = df['volume_change'] * 100
        
        # 计算波动率（价格标准差）
        df['volatility'] = df['close'].rolling(window=20).std()
        
        return df

class RiskAnalyzer:
    """风险分析器"""
    
    def __init__(self):
        self.config = RISK_ANALYSIS_CONFIG
        
    def analyze_risks(self, df):
        """分析风险"""
        if df is None or len(df) < 2:
            return []
            
        risks = []
        latest = df.iloc[-1]
        
        # 检查价格变化风险
        if abs(latest['price_change_pct']) > self.config['price_change_threshold'] * 100:
            risk_level = "HIGH" if abs(latest['price_change_pct']) > 10 else "MEDIUM"
            risks.append({
                'type': 'price_change',
                'level': risk_level,
                'message': f"价格变化异常: {latest['price_change_pct']:.2f}%",
                'value': latest['price_change_pct']
            })
        
        # 检查成交量异常
        if latest['volume_change_pct'] > self.config['volume_spike_threshold'] * 100:
            risks.append({
                'type': 'volume_spike',
                'level': 'HIGH',
                'message': f"成交量突增: {latest['volume_change_pct']:.2f}%",
                'value': latest['volume_change_pct']
            })
        
        # 检查波动率
        if latest['volatility'] > self.config['volatility_threshold']:
            risks.append({
                'type': 'high_volatility',
                'level': 'MEDIUM',
                'message': f"波动率较高: {latest['volatility']:.4f}",
                'value': latest['volatility']
            })
        
        return risks

def display_results(df, risks):
    """显示结果"""
    if OUTPUT_CONFIG['enable_console_output']:
        print("\n" + "="*50)
        print("BTC交易风险提示系统 - 分析结果")
        print("="*50)
        
        if df is not None and len(df) > 0:
            print(f"\n最新价格: ${df.iloc[-1]['close']:.2f}")
            print(f"价格变化: {df.iloc[-1]['price_change_pct']:.2f}%")
            print(f"成交量: {df.iloc[-1]['volume']:.2f}")
            
            # 显示最新数据
            display_rows = min(OUTPUT_CONFIG['max_display_rows'], len(df))
            print(f"\n最新 {display_rows} 条数据:")
            
            # 设置显示格式
            precision = OUTPUT_CONFIG['display_precision']
            pd.set_option('display.float_format', lambda x: f'%.{precision}f' % x)
            
            print(df.tail(display_rows)[['open_time', 'open', 'high', 'low', 'close', 'volume']].to_string(index=False))
        
        # 显示风险提示
        if risks:
            print(f"\n⚠️  发现 {len(risks)} 个风险提示:")
            for i, risk in enumerate(risks, 1):
                level_icon = "🔴" if risk['level'] == 'HIGH' else "🟡"
                print(f"{i}. {level_icon} {risk['message']}")
        else:
            print("\n✅ 当前无明显风险")

def main():
    """主函数"""
    logger.info("=== BTC交易风险提示系统启动 ===")
    
    # 创建数据获取器
    fetcher = BinanceDataFetcher()
    
    # 获取K线数据
    klines_data = fetcher.get_klines()
    
    if klines_data is not None:
        # 创建数据分析器
        analyzer = DataAnalyzer()
        risk_analyzer = RiskAnalyzer()
        
        # 计算技术指标
        klines_data = analyzer.calculate_indicators(klines_data)
        
        # 分析风险
        risks = risk_analyzer.analyze_risks(klines_data)
        
        # 显示结果
        display_results(klines_data, risks)
        
    else:
        logger.error("无法获取数据，系统退出")

if __name__ == "__main__":
    main() 