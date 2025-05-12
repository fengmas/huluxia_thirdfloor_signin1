import hashlib
import json
import os
import random
import time
import requests
from logger import logger
from notifier import get_notifier

# 随机配置
device_model_list = ["iPhone14,3", "iPhone15,2", "iPhone16,1"]  # 随机设备型号
device_code_random = random.randint(1111111111111111, 9999999999999999)  # 随机设备识别码
accept_language_list = [
    "zh-Hans-CN;q=1, en-GB;q=0.9, zh-Hant-CN;q=0.8",
    "zh-Hans-CN;q=1, en-US;q=0.9, ja-JP;q=0.8",
    "zh-Hans-CN;q=1, zh-Hant-TW;q=0.9, en-US;q=0.8"
]  # 随机语言

# 静态配置
ios_app_version = '1.2.2'
market_id = 'floor_huluxia'
platform = '1'  # iOS平台

headers = {
    "Accept": "*/*",
    "Connection": "keep-alive",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": random.choice(accept_language_list),
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": f"Floor/{ios_app_version} (iPhone; iOS 18.2; Scale/3.00)",
    "Host": 'floor.huluxia.com'
}

session = requests.Session()

# 版块id
with open('cat_id.json', 'r', encoding='UTF-8') as f:
    content = f.read()
    cat_id_dict = json.loads(content)

class HuluxiaSignin:
    def __init__(self):
        self._key = ''
        self.userid = ''
        self.device_code = f'[d]{random.randint(1000000000000000, 9999999999999999)}'
        self.device_model = random.choice(device_model_list)
        
    def md5(self, text):
        """生成MD5哈希值（32位小写）"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def ios_login(self, account, password):
        """使用iOS API登录"""
        login_url = 'https://floor.huluxia.com/account/login/IOS/1.0'
        
        login_data = {
            "access_token": "",
            "app_version": ios_app_version,
            "code": "",
            "device_code": self.device_code,
            "device_model": self.device_model,
            "email": "",
            "market_id": market_id,
            "openid": "",
            "password": self.md5(password),  # 密码需要MD5加密
            "phone": "",
            "platform": platform
        }
        
        max_retries = 3
        for retry in range(max_retries):
            try:
                logger.info(f"正在使用iOS API登录账号: {account}")
                login_res = session.post(url=login_url, data=login_data, headers=headers, timeout=15)
                login_res.raise_for_status()  # 检查HTTP状态码
                
                result = login_res.json()
                if result.get("status") == 1:  # 登录成功
                    self._key = result.get("_key", "")
                    self.userid = result.get("user", {}).get("userID", "")
                    logger.info(f"iOS API登录成功: 用户ID={self.userid}")
                    return True
                else:
                    logger.error(f"iOS API登录失败: {result.get('msg', '未知错误')}")
                    # 如果是QQ绑定问题，给出提示
                    if "QQ" in result.get('msg', ''):
                        logger.warning("提示：如果账号已绑定QQ，可能需要先解绑QQ才能正常登录")
                    return False
            except requests.exceptions.RequestException as e:
                if retry < max_retries - 1:
                    logger.warning(f"登录请求失败，正在重试 ({retry + 1}/{max_retries}): {e}")
                    time.sleep(5)  # 等待5秒后重试
                else:
                    logger.error(f"登录请求失败，已达到最大重试次数: {e}")
                    return False
    
    def psd_login(self, account, password):
        """保留原有的安卓登录方式，以备不时之需"""
        # 原有代码保持不变...
        pass
    
    def huluxia_signin(self, phone, password):
        """执行签到流程"""
        # 尝试使用iOS API登录
        login_success = self.ios_login(phone, password)
        
        if not login_success:
            # 如果iOS登录失败，可以选择尝试安卓登录
            logger.warning("iOS登录失败，尝试使用安卓API登录")
            login_success = self.psd_login(phone, password)
            
        if not login_success:
            raise Exception("登录失败，无法继续执行签到")
        
        # 后续签到逻辑保持不变...
        # ...
