"""
乐仔生活 - 多账号自动化任务脚本（iOS版本）
苹果应用商店搜索: 乐仔生活

功能说明：

支持多账号，通过环境变量名称 lzsh 配置
（多个 token 用 @ 符号分隔）

依赖安装：
    安装Python依赖: requests 和 pycryptodome

环境变量配置：
    export lzsh='token1@token2@token3'

获取token方法：
    1. 下载乐仔生活APP
    2. 登录后抓包，找到请求头中的 xiaoletoken 值

"""

import os
import sys
import time
import random
import base64
import json
import requests
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

_PRIVATE_KEY_PEM = """-----BEGIN PRIVATE KEY-----
MIICdQIBADANBgkqhkiG9w0BAQEFAASCAl8wggJbAgEAAoGBAMvDVcWI2hzbZNKc6w2hKR7ySUscYcOM6cOGBoi3RyYovUcugqdzL7lmUPHphDeMCbFeGm++ZEfTbhEVOpeFklaeC0ZH70AzyH9fzGrZDXOHTp6B4HBF72oXWbgZd4ylZf2T7pQj5xBq4qdNG2fQajCgJwA/HcjBgNp64oX7L+ohAgMBAAECgYBWa96xDT4VByhX+53mBfh+25wic0MzwUxUVT/oNHPEx3qf+iYIB16yb6bdM4GUXZyu0Y683i+CFzaToEFdipVpzY9RxT7A3XCVHcvA+140OBpeFELjNDmhjWfTphAoivO6H75Rtqv7LTzE7VtV+gEiNYO480YUV06PpgkwnxBfwQJBAOkJeqWkR9NxlPdE5j1FtxF0oYCI/VlFQxh7gOw2FHIcSRj8+kwlrmaIPzI5BocFY1dPaCVpGJD1Lj2949MLiZUCQQDf12YikHexaSC5pIWvWYPj1NjzoNa7VBP+vqvB5/+YTN0CSgo7ZDwY++R+WXPXdNND2dsCw3btgdigFlCqLXNdAkBF9s6XxIa7+LHcuxbU9oVL/FQwnvBRSPYn94xxXpss10kq82jCS93ccrNmhLBtATUeFX0THkZ93t6PMt+fkSsxAkBfyMB/0eomFKJYTjqWimuRtqcPuaepiZT00YqV8zzAY0O/kwdF2uKMnl1sY8LaU7eDtVmumQ3vHD0iY+ooqEJRAkAfZlDLuMa677vkbhwEV5ZqFPWqawhh/vO0O6ktrz8W8Q98kt2iAnfmwiz61McJfv51Lj04GXqwn/QUAYV9yJMc
-----END PRIVATE KEY-----"""

HEADERS_TEMPLATE = {
    "User-Agent": "%E4%B9%90%E4%BB%94%E7%94%9F%E6%B4%BB/11 CFNetwork/1410.0.3 Darwin/22.6.0",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "x-client-version": "1.2.1",
    "x-os": "ios",
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
}

# 隐藏任务
HIDDEN_TASKS = [
    {"task_id": 106, "name": "同学都在玩消消乐"},
    {"task_id": 107, "name": "免费看短剧得积分"},
    {"task_id": 108, "name": "京东寄快递有减免"},
    {"task_id": 113, "name": "霸王餐任性吃"},
    {"task_id": 114, "name": "浏览网页得积分"},
    {"task_id": 216, "name": "扫码积分派发任务"},
    {"task_id": 218, "name": "免费领优酷会员"},
]

SKIP_TASK_IDS = {150, 151}


def generate_signature(task_id):
    """生成任务签名"""
    chars = '0123456789abcdefghijklmnopqrstuvwxyz'
    random_str = ''.join(random.choices(chars, k=7))
    timestamp = int(time.time() * 1000)
    sign_str = f"{task_id}_{random_str}_{timestamp}_xiaolelife"

    key = RSA.import_key(_PRIVATE_KEY_PEM)
    h = SHA256.new(sign_str.encode('utf-8'))
    signature = pkcs1_15.new(key).sign(h)
    signed_text = base64.b64encode(signature).decode('utf-8')

    return {
        'taskId': task_id,
        'random': random_str,
        'timestamp': timestamp,
        'signedText': signed_text
    }


def get_all_tasks(token):
    url = "https://infor.leyaoyao.com/infor/xiaolelife/points/wall/v4"
    headers = HEADERS_TEMPLATE.copy()
    headers['xiaoletoken'] = token

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        if data.get('code') != '0000000':
            print(f"获取任务列表失败: {data.get('message')}")
            return []

        tasks = []
        types = data.get('body', {}).get('types', [])
        for type_item in types:
            type_name = type_item.get('typeName', '未知分类')
            for task in type_item.get('tasks', []):
                task_id = task.get('taskId')
                if not task_id:
                    continue
                
                if task_id in SKIP_TASK_IDS:
                    continue
                tasks.append({
                    'task_id': task_id,
                    'name': task.get('name', f'任务{task_id}'),
                    'point': task.get('point', 0),
                    'limit': task.get('limit', 0),
                    'done': task.get('doneCount', 0),
                    'route_type': task.get('routeType', ''),
                    'type_name': type_name,
                })
        return tasks
    except Exception as e:
        print(f"获取任务列表异常: {e}")
        return []


def mark_task_finished(token, task_id):
    url = "https://infor.leyaoyao.com/infor/xiaolelife/points/mark-finished"
    headers = HEADERS_TEMPLATE.copy()
    headers['xiaoletoken'] = token
    payload = generate_signature(task_id)

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        data = resp.json()
        if data.get('code') == '0000000':
            points = data.get('body', {}).get('points', 0)
            return points if points is not None else 0
        else:
            print(f"    接口返回错误: {data.get('message')}")
            return -1
    except Exception as e:
        print(f"    请求异常: {e}")
        return -1


def process_hidden_tasks(token, account_idx):
    print(f"\n📦 开始执行隐藏任务（账号 {account_idx+1}）...")
    total_hidden_points = 0

    for task in HIDDEN_TASKS:
        task_id = task["task_id"]
        name = task["name"]
        print(f"  🔍 隐藏任务: {name} (ID:{task_id})")

        attempt = 0
        while True:
            attempt += 1
            gained = mark_task_finished(token, task_id)
            if gained > 0:
                total_hidden_points += gained
                print(f"      第 {attempt} 次: +{gained} 分 (累计 +{total_hidden_points})，继续尝试...")
                time.sleep(random.randint(5, 15))
            elif gained == 0:
                print(f"      第 {attempt} 次: 返回 0 分，停止该任务，进入下一个")
                break
            else:
                print(f"      第 {attempt} 次: 执行失败，停止该任务，进入下一个")
                break

        time.sleep(random.randint(5, 15))

    return total_hidden_points


def process_account(idx, token):
    print(f"\n===== 账号 {idx+1} 开始执行 =====")

    # 1. 获取所有任务（已自动过滤 150、151）
    tasks = get_all_tasks(token)
    if not tasks:
        print("未获取到任务列表，跳过该账号")
        return 0

    total_points = 0
    for task in tasks:
        task_id = task['task_id']
        name = task['name']
        point = task['point']
        limit = task['limit']
        done = task['done']

        remaining = limit - done
        if remaining <= 0:
            print(f"✅ {name} (ID:{task_id}) 已达上限 ({done}/{limit})，跳过")
            continue

        print(f"\n🎯 开始任务: {name} (ID:{task_id}) | 单次积分: {point} | 剩余: {remaining}/{limit}")

        for attempt in range(remaining):
            gained = mark_task_finished(token, task_id)
            if gained >= 0:
                total_points += gained
                print(f"   第{attempt+1}/{remaining}次 +{gained}分 (累计+{total_points})")
            else:
                print(f"   第{attempt+1}次失败，停止该任务")
                break

            if attempt < remaining - 1:
                time.sleep(random.randint(5, 15))

        time.sleep(random.randint(5, 15))

    hidden_points = process_hidden_tasks(token, idx)
    total_points += hidden_points

    print(f"\n本账号获得: {total_points} 分（含隐藏任务 {hidden_points} 分）")
    return total_points


def main():
    print("-" * 30)
    print("乐仔生活 - iOS版")
    print("脚本库: http://2.345yun.cn")
    print("-" * 30)

    tokens_str = os.environ.get("lzsh", "")
    if not tokens_str:
        print("\n未找到环境变量 lzsh")
        print("请在环境变量中添加 lzsh，值为 xiaoletoken")
        print("多个账号用 @ 符号分隔，例如: token1@token2@token3")
        sys.exit(1)

    tokens = [t.strip() for t in tokens_str.split('@') if t.strip()]
    print(f"\n加载了 {len(tokens)} 个账号")

    total_points = 0
    for idx, token in enumerate(tokens):
        points = process_account(idx, token)
        total_points += points

        if idx < len(tokens) - 1:
            wait = random.randint(5, 10)
            print(f"\n等待 {wait} 秒后切换下一个账号...")
            time.sleep(wait)

    print(f"\n{'='*30}")
    print(f"全部完成！总获得积分: {total_points}")
    print(f"{'='*30}")


if __name__ == "__main__":
    main()
