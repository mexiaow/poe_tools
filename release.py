#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 文件名: release.py

import os
import re
import json
import subprocess
import shutil
import requests
from datetime import datetime
from urllib.parse import quote

VERSION_FILE = 'version.txt'  # 存储版本号的文件

# WebDAV配置
WEBDAV_CONFIG = {
    'url': 'https://ali.xiaow.org:8443/dav',
    'username': 'POE2',
    'password': 'g6rz3@DsVN%teuxf',
    'download_url_base': 'https://r2.wlinks.top/Share/POE2PriceAid/'
}

def get_next_version():
    """从version.txt读取当前版本号并计算下一个版本号"""
    try:
        # 检查版本文件是否存在
        if not os.path.exists(VERSION_FILE):
            # 如果不存在，创建初始版本号1.0.0
            with open(VERSION_FILE, 'w', encoding='utf-8') as f:
                f.write('1.0.0')
            return '1.0.1'  # 返回第一个版本号
        
        # 读取当前版本号
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            current_version = f.read().strip()
        
        # 解析版本号
        major, minor, patch = map(int, current_version.split('.'))
        
        # 递增补丁版本号
        patch += 1
        
        # 构建新版本号
        new_version = f"{major}.{minor}.{patch}"
        
        # 保存新版本号到文件
        with open(VERSION_FILE, 'w', encoding='utf-8') as f:
            f.write(new_version)
        
        return new_version
    except Exception as e:
        print(f"❌ 获取下一个版本号失败: {e}")
        # 如果出错，回退到手动输入
        return None

def detect_encoding(file_path):
    """检测文件编码"""
    try:
        # 尝试常见编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'ascii']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read()
                return encoding
            except UnicodeDecodeError:
                continue
        
        # 如果常见编码都失败，尝试使用二进制模式读取前几千字节来猜测
        import chardet
        with open(file_path, 'rb') as f:
            raw_data = f.read(4096)
        result = chardet.detect(raw_data)
        return result['encoding']
    except Exception as e:
        print(f"检测编码失败: {e}")
        return 'utf-8'  # 默认返回utf-8

def update_version_in_source(new_version):
    """更新poe_tools.py中的版本号和更新URL"""
    file_path = 'poe_tools.py'
    version_pattern = r'(self\.current_version\s*=\s*["\'])([0-9.]+)(["\'])'
    url_pattern = r'(self\.update_url\s*=\s*["\'])(https://gitee\.com/mexiaow/poe2-price-aid/raw/main/update\.json)(\?v=[0-9.]+)?(["\'])'
    
    try:
        # 检测文件编码
        encoding = detect_encoding(file_path)
        print(f"检测到文件编码: {encoding}")
        
        # 使用检测到的编码读取文件
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        
        # 替换版本号
        updated_content = re.sub(version_pattern, r'\g<1>' + new_version + r'\g<3>', content)
        
        # 替换更新URL中的版本参数
        updated_content = re.sub(url_pattern, r'\g<1>\g<2>?v=' + new_version + r'\g<4>', updated_content)
        
        # 使用相同的编码写回文件
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(updated_content)
        
        print(f"✅ 已将poe_tools.py中的版本号更新为: {new_version}")
        print(f"✅ 已更新update_url中的版本参数为: ?v={new_version}")
        return True
    except Exception as e:
        print(f"❌ 更新poe_tools.py版本号和URL失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_json_file(version):
    """更新update.json文件中的版本号和下载URL"""
    # 使用WebDAV下载URL
    download_url = f"{WEBDAV_CONFIG['download_url_base']}POE2PriceAid_v{version}.exe"
    
    try:
        # 创建新的update.json内容
        data = {
            'version': version,
            'download_url': download_url,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 写入update.json
        with open('update.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已更新update.json: 版本 {version}, 下载URL {download_url}")
        return True
    except Exception as e:
        print(f"❌ 更新update.json失败: {e}")
        return False

def upload_to_webdav(version):
    """将程序和update.json上传到WebDAV服务器，并只保留最新的5个版本"""
    print("📤 正在上传文件到WebDAV服务器...")
    
    try:
        # 准备要上传的文件
        exe_file = os.path.join("dist", f"POE2PriceAid_v{version}.exe")
        json_file = "update.json"
        
        # 检查文件是否存在
        if not os.path.exists(exe_file):
            print(f"❌ 可执行文件不存在: {exe_file}")
            
            # 尝试在dist目录下查找匹配的文件
            dist_files = []
            for root, dirs, files in os.walk("dist"):
                for file in files:
                    if file.startswith("POE2PriceAid") and file.endswith(".exe"):
                        dist_files.append(os.path.join(root, file))
            
            if dist_files:
                # 使用找到的第一个文件
                exe_file = dist_files[0]
                print(f"找到打包文件: {exe_file}")
            else:
                print("❌ 在dist目录中未找到任何POE2PriceAid*.exe文件")
                return False
        
        if not os.path.exists(json_file):
            print(f"❌ update.json文件不存在")
            return False
        
        # 上传可执行文件
        with open(exe_file, 'rb') as f:
            exe_data = f.read()
        
        exe_response = requests.put(
            f"{WEBDAV_CONFIG['url']}/POE2PriceAid_v{version}.exe",
            data=exe_data,
            auth=(WEBDAV_CONFIG['username'], WEBDAV_CONFIG['password']),
            headers={'Content-Type': 'application/octet-stream'}
        )
        
        if exe_response.status_code not in (200, 201, 204):
            print(f"❌ 上传可执行文件失败: HTTP {exe_response.status_code}")
            return False
        
        # 上传update.json文件
        with open(json_file, 'rb') as f:
            json_data = f.read()
        
        json_response = requests.put(
            f"{WEBDAV_CONFIG['url']}/update.json",
            data=json_data,
            auth=(WEBDAV_CONFIG['username'], WEBDAV_CONFIG['password']),
            headers={'Content-Type': 'application/json'}
        )
        
        if json_response.status_code not in (200, 201, 204):
            print(f"❌ 上传update.json文件失败: HTTP {json_response.status_code}")
            return False
        
        print(f"✅ 文件上传成功")
        print(f"  - 可执行文件: {WEBDAV_CONFIG['url']}/POE2PriceAid_v{version}.exe")
        print(f"  - update.json: {WEBDAV_CONFIG['url']}/update.json")
        print(f"  - 下载链接: {WEBDAV_CONFIG['download_url_base']}POE2PriceAid_v{version}.exe")
        
        # 清理旧版本，只保留最新的5个版本
        clean_old_versions()
        
        # 清理本地dist文件夹，只保留最新的5个版本
        clean_local_dist_folder()
        
        return True
    except Exception as e:
        print(f"❌ 上传到WebDAV失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def clean_old_versions():
    """清理WebDAV服务器上的旧版本，只保留最新的5个版本"""
    print("🧹 正在检查并清理旧版本...")
    try:
        # 使用PROPFIND方法获取WebDAV服务器上的文件列表
        headers = {
            'Depth': '1',  # 只获取当前目录的文件，不包括子目录
            'Content-Type': 'application/xml'
        }
        
        response = requests.request(
            'PROPFIND',
            WEBDAV_CONFIG['url'],
            auth=(WEBDAV_CONFIG['username'], WEBDAV_CONFIG['password']),
            headers=headers
        )
        
        if response.status_code != 207:  # 207是WebDAV的Multi-Status响应
            print(f"❌ 获取文件列表失败: HTTP {response.status_code}")
            return False
        
        # 解析XML响应，提取文件名
        from xml.etree import ElementTree as ET
        root = ET.fromstring(response.content)
        
        # 查找所有POE2PriceAid_v*.exe文件
        version_files = []
        for response_elem in root.findall('.//{DAV:}response'):
            href = response_elem.find('.//{DAV:}href').text
            filename = os.path.basename(href)
            
            # 匹配POE2PriceAid_v*.exe文件
            match = re.match(r'POE2PriceAid_v(\d+\.\d+\.\d+)\.exe', filename)
            if match:
                version = match.group(1)
                version_files.append((version, filename))
        
        # 按版本号排序（从新到旧）
        version_files.sort(key=lambda x: [int(n) for n in x[0].split('.')], reverse=True)
        
        # 如果版本数量超过5个，删除旧版本
        if len(version_files) > 5:
            print(f"发现 {len(version_files)} 个版本，将只保留最新的5个版本")
            
            # 保留最新的5个版本
            keep_versions = version_files[:5]
            delete_versions = version_files[5:]
            
            # 打印将保留的版本
            print("将保留以下版本:")
            for version, filename in keep_versions:
                print(f"  - {filename}")
            
            # 删除旧版本
            print("正在删除以下旧版本:")
            for version, filename in delete_versions:
                print(f"  - {filename}")
                
                # 发送DELETE请求删除文件
                delete_response = requests.delete(
                    f"{WEBDAV_CONFIG['url']}/{filename}",
                    auth=(WEBDAV_CONFIG['username'], WEBDAV_CONFIG['password'])
                )
                
                if delete_response.status_code not in (200, 204):
                    print(f"    ❌ 删除失败: HTTP {delete_response.status_code}")
                else:
                    print(f"    ✅ 删除成功")
            
            print("✅ 旧版本清理完成")
        else:
            print(f"当前共有 {len(version_files)} 个版本，不需要清理")
        
        return True
    except Exception as e:
        print(f"❌ 清理旧版本失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def clean_local_dist_folder():
    """清理本地dist文件夹中的旧版本，只保留最新的5个版本"""
    print("🧹 正在检查并清理本地dist文件夹中的旧版本...")
    try:
        dist_folder = "dist"
        if not os.path.exists(dist_folder) or not os.path.isdir(dist_folder):
            print(f"❌ dist文件夹不存在")
            return False
        
        # 获取dist文件夹中所有的POE2PriceAid_v*.exe文件
        version_files = []
        for filename in os.listdir(dist_folder):
            # 匹配POE2PriceAid_v*.exe文件
            match = re.match(r'POE2PriceAid_v(\d+\.\d+\.\d+)\.exe', filename)
            if match:
                version = match.group(1)
                version_files.append((version, filename))
        
        # 按版本号排序（从新到旧）
        version_files.sort(key=lambda x: [int(n) for n in x[0].split('.')], reverse=True)
        
        # 如果版本数量超过5个，删除旧版本
        if len(version_files) > 5:
            print(f"本地dist文件夹中发现 {len(version_files)} 个版本，将只保留最新的5个版本")
            
            # 保留最新的5个版本
            keep_versions = version_files[:5]
            delete_versions = version_files[5:]
            
            # 打印将保留的版本
            print("将保留以下版本:")
            for version, filename in keep_versions:
                print(f"  - {filename}")
            
            # 删除旧版本
            print("正在删除以下旧版本:")
            for version, filename in delete_versions:
                file_path = os.path.join(dist_folder, filename)
                print(f"  - {filename}")
                
                try:
                    os.remove(file_path)
                    print(f"    ✅ 删除成功")
                except Exception as e:
                    print(f"    ❌ 删除失败: {e}")
            
            print("✅ 本地dist文件夹清理完成")
        else:
            print(f"本地dist文件夹中当前共有 {len(version_files)} 个版本，不需要清理")
        
        return True
    except Exception as e:
        print(f"❌ 清理本地dist文件夹失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_syntax():
    """检查poe_tools.py的语法"""
    print("🔍 检查poe_tools.py语法...")
    try:
        result = subprocess.run(['python', '-m', 'py_compile', 'poe_tools.py'], 
                               capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ 语法检查失败！错误信息:")
            print(result.stderr)
            return False
        print("✅ 语法检查通过")
        return True
    except Exception as e:
        print(f"❌ 语法检查失败: {e}")
        return False

def clean_cache_before_packaging():
    """在打包前清理缓存目录，确保字体大小一致"""
    print("🧹 正在清理缓存目录...")
    try:
        # 获取可能的缓存目录
        cache_dirs = []
        
        # Windows缓存目录
        if os.name == 'nt':
            localappdata = os.environ.get('LOCALAPPDATA', '')
            if localappdata:
                cache_dirs.append(os.path.join(localappdata, 'POE2PriceAid', 'cache'))
                cache_dirs.append(os.path.join(localappdata, 'POE2PriceAid'))
                # PyQt缓存目录
                cache_dirs.append(os.path.join(localappdata, 'PyQt5', 'cache'))
                cache_dirs.append(os.path.join(localappdata, 'PyQt5'))
        
        # Linux/Mac缓存目录
        home = os.path.expanduser('~')
        cache_dirs.append(os.path.join(home, '.cache', 'POE2PriceAid'))
        cache_dirs.append(os.path.join(home, '.cache', 'PyQt5'))
        
        # 项目目录中的缓存
        cache_dirs.append(os.path.join(os.getcwd(), 'cache'))
        cache_dirs.append(os.path.join(os.getcwd(), '.cache'))
        cache_dirs.append(os.path.join(os.getcwd(), '__pycache__'))
        
        # 清理所有可能的缓存目录
        cleaned = False
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                print(f"  - 清理缓存目录: {cache_dir}")
                try:
                    # 遍历缓存目录中的所有文件和子目录
                    for root, dirs, files in os.walk(cache_dir, topdown=False):
                        # 删除所有文件
                        for file in files:
                            try:
                                os.remove(os.path.join(root, file))
                            except Exception as e:
                                print(f"    无法删除文件 {os.path.join(root, file)}: {e}")
                        
                        # 删除所有子目录
                        for dir in dirs:
                            try:
                                shutil.rmtree(os.path.join(root, dir), ignore_errors=True)
                            except Exception as e:
                                print(f"    无法删除目录 {os.path.join(root, dir)}: {e}")
                    
                    cleaned = True
                except Exception as e:
                    print(f"  - 清理目录 {cache_dir} 时出错: {e}")
        
        # 清理PyQt5编译的UI文件
        pyc_files = []
        for root, dirs, files in os.walk(os.getcwd()):
            for file in files:
                if file.endswith('.pyc') or file.endswith('.pyo'):
                    pyc_files.append(os.path.join(root, file))
        
        if pyc_files:
            print(f"  - 清理 {len(pyc_files)} 个编译的Python文件")
            for pyc_file in pyc_files:
                try:
                    os.remove(pyc_file)
                except Exception as e:
                    print(f"    无法删除文件 {pyc_file}: {e}")
        
        if cleaned:
            print("✅ 缓存目录清理完成")
        else:
            print("ℹ️ 未找到需要清理的缓存目录")
        
        return True
    except Exception as e:
        print(f"❌ 清理缓存目录时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_pyinstaller():
    """运行PyInstaller打包应用"""
    print("🔧 正在打包应用程序...")
    try:
        # 使用已有的spec文件进行打包，不添加额外选项
        result = subprocess.run(['pyinstaller', 'poe_tools.spec'], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("❌ 打包失败！错误信息:")
            print(result.stderr)
            return False
        
        print("✅ 应用程序打包成功")
        return True
    except Exception as e:
        print(f"❌ 执行pyinstaller命令失败: {e}")
        return False

def copy_to_desktop(version):
    """将打包好的程序复制到桌面"""
    print("📋 正在将程序复制到桌面...")
    try:
        # 获取桌面路径
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        
        # 打包后的文件路径（带版本号）
        source_file = os.path.join("dist", f"POE2PriceAid_v{version}.exe")
        
        # 如果以上路径不存在，尝试在dist目录下查找匹配的文件
        if not os.path.exists(source_file):
            print(f"在 {source_file} 路径未找到文件，正在搜索dist目录...")
            
            # 查找dist目录下所有可能的POE2PriceAid*.exe文件
            dist_files = []
            for root, dirs, files in os.walk("dist"):
                for file in files:
                    if file.startswith("POE2PriceAid") and file.endswith(".exe"):
                        dist_files.append(os.path.join(root, file))
            
            if dist_files:
                # 使用找到的第一个文件
                source_file = dist_files[0]
                print(f"找到打包文件: {source_file}")
            else:
                print("❌ 在dist目录中未找到任何POE2PriceAid*.exe文件")
                return False
        
        # 目标文件路径(带版本号)
        dest_file = os.path.join(desktop_path, f"POE2PriceAid_v{version}.exe")
        
        # 检查源文件是否存在
        if not os.path.exists(source_file):
            print(f"❌ 源文件不存在: {source_file}")
            return False
            
        # 复制文件到桌面
        shutil.copy2(source_file, dest_file)
        print(f"✅ 程序已复制到桌面: {dest_file}")
        return True
    except Exception as e:
        print(f"❌ 复制到桌面失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数，协调整个发布流程"""
    print("\n===================================")
    print("      POE2PriceAid 发布工具")
    print("===================================\n")
    
    # 获取下一个版本号
    new_version = get_next_version()
    
    # 如果自动获取版本号失败，则回退到手动输入
    if not new_version:
        while True:
            new_version = input("自动获取版本号失败，请手动输入新版本号 (例如 1.0.3): ").strip()
            if new_version and re.match(r'^\d+\.\d+\.\d+$', new_version):
                break
            print("❌ 无效的版本号格式，请使用 x.y.z 格式 (例如 1.0.3)")
    else:
        print(f"自动递增版本号: {new_version}")
    
    # 确认操作
    print(f"\n您将发布的版本号是: {new_version}")
    confirm = input("确认继续? (Y/N, 默认Y): ").strip().upper()
    if confirm == 'N':
        print("已取消操作")
        return
    
    print("\n🚀 开始执行发布流程...\n")
    
    # 1. 更新poe_tools.py中的版本号
    if not update_version_in_source(new_version):
        return
    
    # 2. 更新update.json
    if not update_json_file(new_version):
        return
    
    # 3. 检查语法
    if not check_syntax():
        print("\n⚠️ 警告: poe_tools.py存在语法错误，请修复后再继续")
        return
    
    # 4. 在打包前清理缓存
    if not clean_cache_before_packaging():
        print("\n⚠️ 警告: 清理缓存失败，可能会影响字体大小一致性")
        confirm = input("是否继续打包? (Y/N, 默认Y): ").strip().upper()
        if confirm == 'N':
            print("已取消操作")
            return
    
    # 5. 运行PyInstaller
    if not run_pyinstaller():
        return
    
    # 6. 复制到桌面
    copy_to_desktop(new_version)
    
    # 7. 上传到WebDAV
    if not upload_to_webdav(new_version):
        print("\n⚠️ 警告: 上传到WebDAV失败，请手动上传文件")
    
    print("\n✨ 发布流程完成! ✨")
    print(f"版本号: {new_version}")
    print("\n📋 后续步骤:")
    print(f"1. 程序已打包到dist文件夹，并复制到桌面")
    print(f"2. 程序和update.json已上传到WebDAV服务器")
    print(f"3. 下载链接: {WEBDAV_CONFIG['download_url_base']}POE2PriceAid_v{new_version}.exe")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
    
    input("\n按Enter键退出...")
