import hashlib
import json
import os
import random
import time
import requests
from datetime import datetime, timedelta
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
try:
    with open('cat_id.json', 'r', encoding='UTF-8') as f:
        content = f.read()
        cat_id_dict = json.loads(content)
except FileNotFoundError:
    logger.error("cat_id.json 文件不存在，无法获取版块信息")
    cat_id_dict = {}

class HuluxiaSignin:
    def __init__(self):
        self._key = ''
        self.userid = ''
        self.device_code = f'[d]{random.randint(1000000000000000, 9999999999999999)}'
        self.device_model = random.choice(device_model_list)
        self.login_cache_file = 'huluxia_login_cache.json'  # 缓存文件路径
        
    def md5(self, text):
        """生成MD5哈希值（32位小写）"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def load_cached_login(self, account):
        """加载缓存的登录信息"""
        if not os.path.exists(self.login_cache_file):
            return False
            
        try:
            with open(self.login_cache_file, 'r') as f:
                cache = json.load(f)
                
            # 检查是否有该账号的缓存
            if account in cache:
                cached_data = cache[account]
                
                # 检查缓存是否过期（设置为1天）
                expire_time = datetime.fromisoformat(cached_data.get('expire_time', '1970-01-01T00:00:00'))
                if datetime.now() < expire_time:
                    self._key = cached_data.get('_key', '')
                    self.userid = cached_data.get('userid', '')
                    self.device_code = cached_data.get('device_code', self.device_code)
                    self.device_model = cached_data.get('device_model', self.device_model)
                    logger.info(f"成功加载缓存的登录信息: 用户ID={self.userid}")
                    return True
                else:
                    logger.info("缓存的登录信息已过期，需要重新登录")
            else:
                logger.info(f"没有找到账号 {account} 的缓存登录信息")
                
        except Exception as e:
            logger.warning(f"加载缓存登录信息失败: {e}")
            
        return False
        
    def save_login_to_cache(self, account):
        """保存登录信息到缓存"""
        try:
            # 读取现有缓存
            cache = {}
            if os.path.exists(self.login_cache_file):
                with open(self.login_cache_file, 'r') as f:
                    try:
                        cache = json.load(f)
                    except json.JSONDecodeError:
                        cache = {}
            
            # 更新缓存
            expire_time = (datetime.now() + timedelta(days=1)).isoformat()
            cache[account] = {
                '_key': self._key,
                'userid': self.userid,
                'device_code': self.device_code,
                'device_model': self.device_model,
                'expire_time': expire_time
            }
            
            # 保存缓存
            with open(self.login_cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
                
            logger.info(f"已保存登录信息到缓存，有效期至: {expire_time}")
            
        except Exception as e:
            logger.warning(f"保存登录信息到缓存失败: {e}")
    
    def verify_login(self):
        """验证当前登录信息是否有效"""
        if not self._key or not self.userid:
            return False
            
        # 可以添加一个简单的API调用验证登录状态
        try:
            verify_url = f"https://floor.huluxia.com/user/getUserInfoByUid/IOS/1.0?_key={self._key}&userID={self.userid}"
            response = session.get(verify_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            return result.get("status") == 1
        except Exception as e:
            logger.warning(f"验证登录信息失败: {e}")
            return False
    
    def ios_login(self, account, password):
        """使用iOS API登录，优先使用缓存"""
        # 尝试加载缓存的登录信息
        if self.load_cached_login(account):
            # 验证缓存的登录信息是否有效
            if self.verify_login():
                return True
        
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
                    
                    # 保存登录信息到缓存
                    self.save_login_to_cache(account)
                    
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
        login_url = 'http://floor.huluxia.com/account/login/ANDROID/4.0?' \
                    'platform=2' \
                    '&gkey=000000' \
                    '&app_version=4.3.1.5.2' \
                    '&versioncode=398' \
                    '&market_id=floor_web' \
                    '&_key=&device_code=' + self.device_code + \
                    '&phone_brand_type=Huawei'
        
        login_data = {
            'account': account,
            'password': self.md5(password),
            'login_type': 2
        }
        
        max_retries = 3
        for retry in range(max_retries):
            try:
                logger.info(f"正在使用安卓API登录账号: {account}")
                login_res = session.post(url=login_url, data=login_data, headers=headers, timeout=15)
                login_res.raise_for_status()  # 检查HTTP状态码
                
                result = login_res.json()
                if result.get("status") == 1:  # 登录成功
                    self._key = result.get("_key", "")
                    self.userid = result.get("user", {}).get("userID", "")
                    logger.info(f"安卓API登录成功: 用户ID={self.userid}")
                    return True
                else:
                    logger.error(f"安卓API登录失败: {result.get('msg', '未知错误')}")
                    return False
            except requests.exceptions.RequestException as e:
                if retry < max_retries - 1:
                    logger.warning(f"登录请求失败，正在重试 ({retry + 1}/{max_retries}): {e}")
                    time.sleep(5)  # 等待5秒后重试
                else:
                    logger.error(f"登录请求失败，已达到最大重试次数: {e}")
                    return False
    
    def sign_in_to_board(self, board_id, board_name):
        """签到指定版块"""
        try:
            sign_url = f"https://floor.huluxia.com/signin/add/IOS/1.0?_key={self._key}&userID={self.userid}"
            
            sign_data = {
                "cat_id": board_id,
                "user_id": self.userid
            }
            
            response = session.post(sign_url, data=sign_data, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("status") == 1:
                logger.info(f"成功签到版块: {board_name}")
                return True
            else:
                logger.warning(f"签到版块 {board_name} 失败: {result.get('msg', '未知错误')}")
                return False
        except Exception as e:
            logger.error(f"签到版块 {board_name} 时发生异常: {e}")
            return False
    
    def get_user_info(self):
        """获取用户信息"""
        try:
            url = f"https://floor.huluxia.com/user/getUserInfoByUid/IOS/1.0?_key={self._key}&userID={self.userid}"
            response = session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("status") == 1:
                user_info = result.get("user", {})
                logger.info(f"用户信息: 昵称={user_info.get('nick', '未知')}, 等级={user_info.get('level', '未知')}")
                return user_info
            else:
                logger.warning(f"获取用户信息失败: {result.get('msg', '未知错误')}")
                return None
        except Exception as e:
            logger.error(f"获取用户信息时发生异常: {e}")
            return None
    
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
            
        # 获取用户信息
        user_info = self.get_user_info()
        
        # 签到所有版块
        if cat_id_dict:
            success_count = 0
            total_count = len(cat_id_dict)
            
            logger.info(f"开始签到所有版块，共 {total_count} 个版块")
            
            for board_id, board_name in cat_id_dict.items():
                if self.sign_in_to_board(board_id, board_name):
                    success_count += 1
                # 防止请求过于频繁
                time.sleep(2)
            
            logger.info(f"签到完成: 成功 {success_count}/{total_count} 个版块")
            
            # 通知签到结果
            notifier = get_notifier()
            if notifier:
                if user_info:
                    nick = user_info.get('nick', '未知用户')
                else:
                    nick = '未知用户'
                    
                message = f"账号 {phone} ({nick}) 签到完成\n" \
                         f"成功: {success_count}/{total_count} 个版块"
                notifier.send(message)
        else:
            logger.warning("没有可用的版块信息，跳过签到")
