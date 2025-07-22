#!/usr/bin/env python3
"""
网络连接测试脚本
用于诊断币安API连接问题
"""

import requests
import ssl
import urllib3
from config import BINANCE_API_CONFIG, DATA_FETCH_CONFIG

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_basic_connection():
    """测试基本连接"""
    print("=== 测试基本网络连接 ===")
    
    try:
        # 测试基本HTTP连接
        response = requests.get('https://httpbin.org/get', timeout=10)
        print(f"✅ 基本HTTP连接正常: {response.status_code}")
    except Exception as e:
        print(f"❌ 基本HTTP连接失败: {e}")
        return False
    
    return True

def test_binance_api():
    """测试币安API连接"""
    print("\n=== 测试币安API连接 ===")
    
    # 测试不同的连接方式
    test_configs = [
        {
            'name': '标准连接',
            'verify': True,
            'proxies': {}
        },
        {
            'name': '禁用SSL验证',
            'verify': False,
            'proxies': {}
        },
        {
            'name': '禁用代理',
            'verify': False,
            'proxies': {}
        }
    ]
    
    for config in test_configs:
        try:
            print(f"\n尝试 {config['name']}...")
            
            session = requests.Session()
            session.verify = config['verify']
            session.proxies = config['proxies']
            session.headers.update({
                'User-Agent': DATA_FETCH_CONFIG['user_agent']
            })
            
            params = {
                'symbol': 'BTCUSDT',
                'interval': '1h',
                'limit': 5  # 只获取5条数据用于测试
            }
            
            response = session.get(
                BINANCE_API_CONFIG['base_url'],
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {config['name']} 成功! 获取到 {len(data)} 条数据")
                if data:
                    latest_price = float(data[-1][4])  # 最新收盘价
                    print(f"   最新BTC价格: ${latest_price:,.2f}")
                return True
            else:
                print(f"❌ {config['name']} 失败: HTTP {response.status_code}")
                
        except requests.exceptions.SSLError as e:
            print(f"❌ {config['name']} SSL错误: {e}")
        except requests.exceptions.ProxyError as e:
            print(f"❌ {config['name']} 代理错误: {e}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {config['name']} 请求错误: {e}")
        except Exception as e:
            print(f"❌ {config['name']} 未知错误: {e}")
    
    return False

def test_ssl_context():
    """测试SSL上下文"""
    print("\n=== 测试SSL上下文 ===")
    
    try:
        # 创建SSL上下文
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        print("✅ SSL上下文创建成功")
        return True
    except Exception as e:
        print(f"❌ SSL上下文创建失败: {e}")
        return False

def main():
    """主函数"""
    print("BTC交易系统 - 网络连接诊断工具")
    print("=" * 50)
    
    # 显示当前配置
    print(f"API地址: {BINANCE_API_CONFIG['base_url']}")
    print(f"SSL验证: {'启用' if DATA_FETCH_CONFIG['enable_ssl_verify'] else '禁用'}")
    print(f"代理设置: {'启用' if DATA_FETCH_CONFIG['enable_proxy'] else '禁用'}")
    
    # 执行测试
    basic_ok = test_basic_connection()
    ssl_ok = test_ssl_context()
    api_ok = test_binance_api()
    
    # 总结
    print("\n" + "=" * 50)
    print("测试结果总结:")
    print(f"基本网络连接: {'✅ 正常' if basic_ok else '❌ 异常'}")
    print(f"SSL上下文: {'✅ 正常' if ssl_ok else '❌ 异常'}")
    print(f"币安API连接: {'✅ 正常' if api_ok else '❌ 异常'}")
    
    if api_ok:
        print("\n🎉 所有测试通过！系统可以正常运行。")
    else:
        print("\n⚠️  存在连接问题，建议:")
        print("1. 检查网络连接")
        print("2. 检查防火墙设置")
        print("3. 尝试使用VPN")
        print("4. 联系网络管理员")

if __name__ == "__main__":
    main() 