import requests
import time
import hmac
import hashlib
from typing import Dict, List, Optional

from config import BINANCE_BASE_URL, BINANCE_ACCOUNT_ENDPOINT, BINANCE_POSITION_ENDPOINT, USE_PROXY
from api_keys import API_KEY, SECRET_KEY

def make_api_request(endpoint: str, params: Optional[Dict] = None, auth_required: bool = False) -> Optional[Dict]:
    """统一的API请求函数"""
    url = f"{BINANCE_BASE_URL}{endpoint}"
    headers = {}
    proxies = {'http': 'http://127.0.0.1:10809', 'https': 'http://127.0.0.1:10809'} if USE_PROXY else None
    
    try:
        if auth_required:
            if not all([API_KEY, SECRET_KEY]):
                print("请先配置API_KEY和SECRET_KEY")
                return None
            
            timestamp = int(time.time() * 1000)
            query_params = params or {}
            query_params['timestamp'] = timestamp
            
            query_string = '&'.join([f"{k}={v}" for k, v in query_params.items()])
            signature = hmac.new(SECRET_KEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            
            url = f"{url}?{query_string}&signature={signature}"
            headers['X-MBX-APIKEY'] = API_KEY
        else:
            if params:
                query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
                url = f"{url}?{query_string}"
        
        response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"API请求失败: {e}")
        return None

def get_account_info() -> Optional[Dict]:
    """获取账户基本信息"""
    return make_api_request(BINANCE_ACCOUNT_ENDPOINT, auth_required=True)

def get_positions() -> Optional[List]:
    """获取合约持仓信息"""
    return make_api_request(BINANCE_POSITION_ENDPOINT, auth_required=True)