# -*- coding: utf-8 -*-
import re
import os
import shutil
import pickle
import requests
from collections import namedtuple
from urllib3 import disable_warnings

from datetime import timedelta, datetime
from urllib3.exceptions import InsecureRequestWarning
from random import uniform, choices, sample, shuffle, choice
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

"""
蓝奏网盘 API，封装了对蓝奏云的各种操作，解除了上传格式、大小限制
"""

File = namedtuple('File', ['name', 'id', 'time', 'size', 'type', 'downs', 'has_pwd', 'has_des'])
Folder = namedtuple('Folder', ['name', 'id', 'has_pwd', 'desc'])
FolderId = namedtuple('FolderId', ['name', 'id'])

disable_warnings(InsecureRequestWarning)  # 全局禁用 SSL 警告


class ItemList:
    """具有 name, id 属性对象的列表"""

    def __init__(self):
        self._items = []

    def __len__(self):
        return len(self._items)

    def __getitem__(self, index):
        return self._items[index]

    def __iter__(self):
        return iter(self._items)

    def __repr__(self):
        return f"<List {', '.join(it.__str__() for it in self)}>"

    def __lt__(self, other):
        """用于路径 List 之间排序"""
        return '/'.join(i.name for i in self) < '/'.join(i.name for i in other)

    @property
    def name_id(self):
        """所有 item 的 name-id 列表，兼容旧版"""
        return {it.name: it.id for it in self}

    @property
    def all_name(self):
        """所有 item 的 name 列表"""
        return [it.name for it in self]

    def append(self, item):
        """在末尾插入元素"""
        self._items.append(item)

    def index(self, item):
        """获取索引"""
        return self._items.index(item)

    def insert(self, pos, item):
        """指定位置插入元素"""
        self._items.insert(pos, item)

    def clear(self):
        """清空元素"""
        self._items.clear()

    def filter(self, condition) -> list:
        """筛选出满足条件的 item
        condition(item) -> True
        """
        return [it for it in self if condition(it)]

    def find_by_name(self, name: str):
        """使用文件名搜索(仅返回首个匹配项)"""
        for item in self:
            if name == item.name:
                return item
        return None

    def find_by_id(self, fid: int):
        """使用 id 搜索(精确)"""
        for item in self:
            if fid == item.id:
                return item
        return None

    def pop_by_id(self, fid):
        for item in self:
            if item.id == fid:
                self._items.remove(item)
                return item
        return None

    def update_by_id(self, fid, **kwargs):
        """通过 id 搜索元素并更新"""
        item = self.find_by_id(fid)
        pos = self.index(item)
        data = item._asdict()
        data.update(kwargs)
        self._items[pos] = item.__class__(**data)


class FileList(ItemList):
    """文件列表类"""
    pass


class FolderList(ItemList):
    """文件夹列表类"""
    pass


class LanZouCloud(object):
    FAILED = -1
    SUCCESS = 0
    ID_ERROR = 1
    PASSWORD_ERROR = 2
    LACK_PASSWORD = 3
    ZIP_ERROR = 4
    MKDIR_ERROR = 5
    URL_INVALID = 6
    FILE_CANCELLED = 7
    PATH_ERROR = 8
    NETWORK_ERROR = 9
    CAPTCHA_ERROR = 10

    def __init__(self, cookie_str: str):
        self._session = requests.Session()
        self._captcha_handler = None
        self._timeout = 5  # 每个请求的超时(不包含下载响应体的用时)
        self._max_size = 100  # 单个文件大小上限 MB
        self._ylogin = None
        self._vei = None

        self.handler_cookies(cookie_str)  # 处理用户输入的cookie字符串，完成登录
        self._headers = {
            'authority': 'pc.woozooo.com',
            'Origin': 'https://pc.woozooo.com',
            # 'Referer': f'https://pc.woozooo.com/mydisk.php?item=files&action=index&u={self._ylogin}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36',
            'Referer': 'https://www.lanzous.com',
            'Accept-Language': 'zh-CN,zh;q=0.9',  # 提取直连必需设置这个，否则拿不到数据

        }

        self._session.headers = self._headers
        self._cookies = None

        self._index_url = 'https://pc.woozooo.com/'  # 首页：进入该网站时，会设置一个PHPSESSID
        self._host_url = 'https://www.lanzou.com/'  # 注意这个网址，不是https://www.lanzous.com/

        self._do_upload_url = 'https://pc.woozooo.com/html5up.php'  # 更新后的上传链接

        self._account_url = 'https://pc.woozooo.com/account.php'
        self._doupload_url = f'https://pc.woozooo.com/doupload.php?uid={self._ylogin}'  # 原上传链接
        self._my_disk_url = 'https://pc.woozooo.com/mydisk.php'

        if not self.check_cookie():
            raise Exception("输入的cookie无效，无法登录！")

        disable_warnings(InsecureRequestWarning)  # 全局禁用 SSL 警告

    def check_cookie(self) -> bool:
        for i in range(3):  # 防止由于网络原因导致失败，设置重试3次
            response = self._get(self._account_url)
            if not response:
                continue
            return True if '网盘用户登录' not in response.text else False

    def handler_cookies(self, cookie_str):
        cookie_list = cookie_str.split(';')
        cookie_dict = {}
        for item in cookie_list:
            k, v = item.strip().split('=', maxsplit=1)
            cookie_dict[k] = v
        self._ylogin = cookie_dict['ylogin']
        self._session.cookies.update(cookie_dict)

    # 获取文件列表时，需要传入的一个参数
    @property
    def vei(self):

        if self._vei:
            return self._vei

        params = {
            'item': 'files',
            'action': 'index',
            'u': self._ylogin,
        }

        response = self._get(self._my_disk_url, params=params)

        vei_obj = re.compile(r"""data : \{ 'task':47,'folder_id':folder_id,'vei':'(?P<vei>.*?)' }""", re.S)
        result = vei_obj.search(response.text)

        if not result:
            raise Exception("获取vei值失败！")
        self._vei = result.group('vei')
        return self._vei

    def get_file_list(self, folder_id=-1) -> FileList:
        """获取文件列表"""
        page = 1
        file_list = FileList()
        while True:
            post_data = {'task': 5, 'folder_id': folder_id, 'vei': self.vei, 'pg': page}
            headers = {
                'authority': 'pc.woozooo.com',
                'Origin': 'https://pc.woozooo.com',
                'Referer': f'https://pc.woozooo.com/mydisk.php?item=files&action=index&u={self._ylogin}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            }

            resp = self._session.post(self._doupload_url, post_data, headers=headers)
            if not resp:  # 网络异常，重试
                continue
            else:
                resp = resp.json()

            if resp["info"] == 0:
                break  # 已经拿到了全部的文件信息
            else:
                page += 1  # 下一页
            # 文件信息处理
            for file in resp["text"]:
                file_list.append(File(
                    id=int(file['id']),
                    name=file['name_all'],
                    time=time_format(file['time']),  # 上传时间
                    size=file['size'],  # 文件大小
                    type=file['name_all'].split('.')[-1],  # 文件类型
                    downs=int(file['downs']),  # 下载次数
                    has_pwd=True if int(file['onof']) == 1 else False,  # 是否存在提取码
                    has_des=True if int(file['is_des']) == 1 else False  # 是否存在描述
                ))
        return file_list

    def get_dir_list(self, folder_id=-1) -> FolderList:
        """获取子文件夹列表"""
        folder_list = FolderList()
        post_data = {'task': 47, 'folder_id': folder_id, 'vei': self.vei}
        headers = {
            'authority': 'pc.woozooo.com',
            'Origin': 'https://pc.woozooo.com',
            'Referer': f'https://pc.woozooo.com/mydisk.php?item=files&action=index&u={self._ylogin}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        }
        resp = self._post(self._doupload_url, post_data, headers=headers)

        if not resp.content:
            return folder_list
        for folder in resp.json()['text']:
            folder_list.append(
                Folder(
                    id=int(folder['fol_id']),
                    name=folder['name'],
                    has_pwd=True if folder['onof'] == 1 else False,
                    desc=folder['folder_des'].strip('[]')
                ))
        return folder_list

    def get_move_folders(self) -> FolderList:
        """获取全部文件夹 id-name 列表，用于移动文件至新的文件夹"""
        # 这里 file_id 可以为任意值,不会对结果产生影响
        result = FolderList()
        result.append(FolderId(name='LanZouCloud', id=-1))
        resp = self._post(self._doupload_url, data={"task": 19, "file_id": -1})
        if not resp or resp.json()['zt'] != 1:  # 获取失败或者网络异常
            return result
        for folder in resp.json()['info']:
            folder_id, folder_name = int(folder['folder_id']), folder['folder_name']
            result.append(FolderId(folder_name, folder_id))
        return result

    def mkdir(self, parent_id, folder_name, desc='') -> int:
        """创建文件夹(同时设置描述)"""
        folder_name = folder_name.replace(' ', '_')  # 文件夹名称不能包含空格
        folder_name = name_format(folder_name)  # 去除非法字符
        folder_list = self.get_dir_list(parent_id)
        if folder_list.find_by_name(folder_name):  # 如果文件夹已经存在，直接返回 id
            return folder_list.find_by_name(folder_name).id
        raw_folders = self.get_move_folders()
        post_data = {"task": 2, "parent_id": parent_id or -1, "folder_name": folder_name,
                     "folder_description": desc}
        result = self._post(self._doupload_url, post_data)  # 创建文件夹
        if not result or result.json()['zt'] != 1:
            return LanZouCloud.MKDIR_ERROR  # 正常时返回 id 也是 int，为了方便判断是否成功，网络异常或者创建失败都返回相同错误码
        # 允许再不同路径创建同名文件夹, 移动时可通过 get_move_paths() 区分
        for folder in self.get_move_folders():
            if not raw_folders.find_by_id(folder.id):
                return folder.id
        return LanZouCloud.MKDIR_ERROR

    def delete(self, fid, is_file=True) -> int:
        """把网盘的文件、无子文件夹的文件夹放到回收站"""
        post_data = {'task': 6, 'file_id': fid} if is_file else {'task': 3, 'folder_id': fid}
        result = self._post(self._doupload_url, post_data)
        if not result:
            return LanZouCloud.NETWORK_ERROR
        return LanZouCloud.SUCCESS if result.json()['zt'] == 1 else LanZouCloud.FAILED

    def get_file_pwd(self, file_id):

        post_data = {'task': 22, 'file_id': file_id}
        headers = {
            # 'authority': 'pc.woozooo.com',
            # 'Sec-Fetch-Site': 'same-origin',
            # 'Sec-Fetch-Mode': 'cors',
            # 'Sec-Fetch-Dest': 'empty',
            # 'Sec-Ch-Ua-Platform': "Windows",
            # 'Sec-Ch-Ua-Mobile': "?0",
            # 'Sec-Ch-Ua': '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',

            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://pc.woozooo.com',
            'Referer': f'https://pc.woozooo.com/mydisk.php?item=files&action=index&u={self._ylogin}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        }
        resp = self._post(self._doupload_url, post_data, headers=headers)

        data = resp.json()

        pwd = data['info']['pwd']

        return pwd

    def _upload_small_file(self, file_path, folder_id=-1, callback=None):
        """绕过格式限制上传不超过 max_size 的文件"""

        need_delete = False  # 上传完成是否删除
        if not is_name_valid(os.path.basename(file_path)):  # 不允许上传的格式
            file_path = let_me_upload(file_path)  # 添加了报尾的新文件
            need_delete = True

        # 文件已经存在同名文件就删除
        filename = name_format(os.path.basename(file_path))
        file_list = self.get_file_list(folder_id)
        if file_list.find_by_name(filename):
            self.delete(file_list.find_by_name(filename).id)

        file = open(file_path, 'rb')
        post_data = {
            "task": "1",
            "folder_id": str(folder_id),
            "id": "WU_FILE_0",
            "name": filename,
            "upload_file": (filename, file, 'application/octet-stream')
        }

        post_data = MultipartEncoder(post_data)
        tmp_header = self._headers.copy()
        tmp_header['Content-Type'] = post_data.content_type

        # MultipartEncoderMonitor 每上传 8129 bytes数据调用一次回调函数，问题根源是 httplib 库
        # issue : https://github.com/requests/toolbelt/issues/75
        # 上传完成后，回调函数会被错误的多调用一次(强迫症受不了)。因此，下面重新封装了回调函数，修改了接受的参数，并阻断了多余的一次调用
        self._upload_finished_flag = False  # 上传完成的标志

        def _call_back(read_monitor):
            if callback is not None:
                if not self._upload_finished_flag:
                    callback(filename, read_monitor.len, read_monitor.bytes_read)
                if read_monitor.len == read_monitor.bytes_read:
                    self._upload_finished_flag = True

        monitor = MultipartEncoderMonitor(post_data, _call_back)
        result = self._post('https://pc.woozooo.com/fileup.php', data=monitor, headers=tmp_header, timeout=3600)
        if not result:  # 网络异常
            return LanZouCloud.NETWORK_ERROR
        else:
            result = result.json()
        if result["zt"] != 1:
            return LanZouCloud.FAILED  # 上传失败

        file_id = result["text"][0]["id"]
        f_id = result["text"][0]["f_id"]
        is_newd = result["text"][0]["is_newd"]
        # self.set_passwd(file_id)  # 关闭提取码，该功能官方有改动，部分格式无法取消密码
        # 文件上传后，获取该文件密码

        pwd = self.get_file_pwd(file_id)

        if need_delete:
            file.close()
            os.remove(file_path)
        # print(f"文件链接：{is_newd}/{f_id}\n提取密码：{pwd}")
        # return LanZouCloud.SUCCESS
        return {'file_url': f"{is_newd}/{f_id}", 'file_pwd': pwd}

    def _upload_big_file(self, file_path, dir_id, callback=None):
        """上传大文件, 且使得回调函数只显示一个文件"""
        file_size = os.path.getsize(file_path)  # 原始文件的字节大小
        file_name = os.path.basename(file_path)
        tmp_dir = os.path.dirname(file_path) + os.sep + '__' + '.'.join(file_name.split('.')[:-1])  # 临时文件保存路径
        record_file = tmp_dir + os.sep + file_name + '.record'  # 记录文件，大文件没有完全上传前保留，用于支持续传
        uploaded_size = 0  # 记录已上传字节数，用于回调函数

        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
        if not os.path.exists(record_file):  # 初始化记录文件
            info = {'name': file_name, 'size': file_size, 'uploaded': 0, 'parts': []}
            with open(record_file, 'wb') as f:
                pickle.dump(info, f)
        else:
            with open(record_file, 'rb') as f:
                info = pickle.load(f)
                uploaded_size = info['uploaded']  # 读取已经上传的大小

        def _callback(name, t_size, now_size):  # 重新封装回调函数，隐藏数据块上传细节
            nonlocal uploaded_size
            if callback is not None:
                # MultipartEncoder 以后,文件数据流比原文件略大几百字节, now_size 略大于 file_size
                now_size = uploaded_size + now_size
                now_size = now_size if now_size < file_size else file_size  # 99.99% -> 100.00%
                callback(file_name, file_size, now_size)

        while uploaded_size < file_size:
            data_size, data_path = big_file_split(file_path, self._max_size, start_byte=uploaded_size)
            code = self._upload_small_file(data_path, dir_id, _callback)
            if code == LanZouCloud.SUCCESS:
                uploaded_size += data_size  # 更新已上传的总字节大小
                info['uploaded'] = uploaded_size
                info['parts'].append(os.path.basename(data_path))  # 记录已上传的文件名
                with open(record_file, 'wb') as f:

                    pickle.dump(info, f)
            else:

                return LanZouCloud.FAILED

        # 全部数据块上传完成
        record_name = list(file_name.replace('.', ''))  # 记录文件名也打乱
        shuffle(record_name)
        record_name = name_format(''.join(record_name)) + '.txt'
        record_file_new = tmp_dir + os.sep + record_name
        os.rename(record_file, record_file_new)
        code = self._upload_small_file(record_file_new, dir_id)  # 上传记录文件
        if code != LanZouCloud.SUCCESS:
            return LanZouCloud.FAILED
        # 记录文件上传成功，删除临时文件
        shutil.rmtree(tmp_dir)

        return LanZouCloud.SUCCESS

    def upload_file(self, file_path, folder_id=-1, callback=None):
        """解除限制上传文件"""

        # 判断是否为文件
        if not os.path.isfile(file_path):
            return LanZouCloud.PATH_ERROR

        # 单个文件不超过 max_size 直接上传
        if os.path.getsize(file_path) <= self._max_size * 1048576:
            return self._upload_small_file(file_path, folder_id, callback)

        print("文件超过100M，无法上传")
        # 上传超过 max_size 的文件
        # folder_name = os.path.basename(file_path).replace('.', '_mkdir')  # 保存分段文件的文件夹名
        # dir_id = self.mkdir(folder_id, folder_name, 'Big File')
        # if dir_id == LanZouCloud.MKDIR_ERROR:
        #     return LanZouCloud.MKDIR_ERROR  # 创建文件夹失败就退出
        # return self._upload_big_file(file_path, dir_id, callback)

    def _get(self, url, **kwargs):
        try:
            kwargs.setdefault('timeout', self._timeout)
            kwargs.setdefault('headers', self._headers)
            return self._session.get(url, verify=False, **kwargs)
        except (ConnectionError, requests.RequestException):
            return None

    def _post(self, url, data, **kwargs):
        try:
            kwargs.setdefault('timeout', self._timeout)
            kwargs.setdefault('headers', self._headers)
            return self._session.post(url, data, verify=False, **kwargs)
        except (ConnectionError, requests.RequestException):
            return None

    def set_passwd(self, fid, passwd='', is_file=True) -> int:
        """设置网盘文件(夹)的提取码"""
        # id 无效或者 id 类型不对应仍然返回成功 :(
        # 文件夹提取码长度 0-12 位  文件提取码 2-6 位
        passwd_status = 0 if passwd == '' else 1  # 是否开启密码
        if is_file:
            post_data = {"task": 23, "file_id": fid, "shows": passwd_status, "shownames": passwd}
        else:
            post_data = {"task": 16, "folder_id": fid, "shows": passwd_status, "shownames": passwd}

        headers = {
            'authority': 'pc.woozooo.com',
            'Origin': 'https://pc.woozooo.com',
            'Referer': f'https://pc.woozooo.com/mydisk.php?item=files&action=index&u={self._ylogin}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        }
        result = self._post(self._doupload_url, post_data, headers=headers)

        if not result.content:
            return LanZouCloud.NETWORK_ERROR
        return LanZouCloud.SUCCESS if result.json()['zt'] == 1 else LanZouCloud.FAILED

    # 待开发
    def _cookies_get_phpsessid(self):
        """
        登录的第一步：返回主页，进入该主页时，会写入一个cookies：PHPSESSID
        :return:
        """
        try:
            response = self._session.get(self._host_url, headers=self._headers)
        except (ConnectionError, requests.RequestException):
            return None

    # 待开发
    def login(self, username, passwd) -> int:
        """登录蓝奏云控制台"""
        login_data = {"action": "login",
                      "task": "login",
                      "setSessionId": "",
                      "setToken": "",
                      "setSig": "",
                      "setScene": "",
                      "username": username,
                      "password": passwd}
        phone_header = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 5.0; SM-G900P Build/LRX21T) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/82.0.4051.0 Mobile Safari/537.36"}
        html = self._post(self._account_url, data=login_data, headers=phone_header)
        with open('1.html', mode='wb') as f:
            f.write(html.content)

        return 0

    # 待开发
    def login_by_cookie(self, cookie: dict) -> int:
        """通过cookie登录"""
        self._session.cookies.update(cookie)
        html = self._get(self._account_url)
        print(html.text)
        if not html:
            return LanZouCloud.NETWORK_ERROR
        return LanZouCloud.FAILED if '网盘用户登录' in html.text else LanZouCloud.SUCCESS


def time_format(time_str: str) -> str:
    """输出格式化时间 %Y-%m-%d"""
    if '秒前' in time_str or '分钟前' in time_str or '小时前' in time_str:
        return datetime.today().strftime('%Y-%m-%d')
    elif '昨天' in time_str:
        return (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    elif '前天' in time_str:
        return (datetime.today() - timedelta(days=2)).strftime('%Y-%m-%d')
    elif '天前' in time_str:
        days = time_str.replace(' 天前', '')
        return (datetime.today() - timedelta(days=int(days))).strftime('%Y-%m-%d')
    else:
        return time_str


def name_format(name: str) -> str:
    """去除非法字符"""
    name = name.replace(u'\xa0', ' ').replace(u'\u3000', ' ').replace('  ', ' ')  # 去除其它字符集的空白符,去除重复空白字符
    return re.sub(r'[$%^!*<>)(+=`\'\"/:;,?]', '', name)


def big_file_split(file_path: str, max_size: int = 100, start_byte: int = 0) -> (int, str):
    """将大文件拆分为大小、格式随机的数据块, 可指定文件起始字节位置(用于续传)
    :return 数据块文件的大小和绝对路径
    """
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    tmp_dir = os.path.dirname(file_path) + os.sep + '__' + '.'.join(file_name.split('.')[:-1])

    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    def get_random_size() -> int:
        """按权重生成一个不超过 max_size 的文件大小"""
        reduce_size = choices([uniform(0, 20), uniform(20, 30), uniform(30, 60), uniform(60, 80)], weights=[2, 5, 2, 1])
        return round((max_size - reduce_size[0]) * 1048576)

    def get_random_name() -> str:
        """生成一个随机文件名"""
        # 这些格式的文件一般都比较大且不容易触发下载检测
        suffix_list = ('zip', 'rar', 'apk', 'ipa', 'exe', 'pdf', '7z', 'tar', 'deb', 'dmg', 'rpm', 'flac')
        name = list(file_name.replace('.', '').replace(' ', ''))
        name = name + sample('abcdefghijklmnopqrstuvwxyz', 3) + sample('1234567890', 2)
        shuffle(name)  # 打乱顺序
        name = ''.join(name) + '.' + choice(suffix_list)
        return name_format(name)  # 确保随机名合法

    with open(file_path, 'rb') as big_file:
        big_file.seek(start_byte)
        left_size = file_size - start_byte  # 大文件剩余大小
        random_size = get_random_size()
        tmp_file_size = random_size if left_size > random_size else left_size
        tmp_file_path = tmp_dir + os.sep + get_random_name()

        chunk_size = 524288  # 512KB
        left_read_size = tmp_file_size
        with open(tmp_file_path, 'wb') as small_file:
            while left_read_size > 0:
                if left_read_size < chunk_size:  # 不足读取一次
                    small_file.write(big_file.read(left_read_size))
                    break
                # 一次读取一块,防止一次性读取占用内存
                small_file.write(big_file.read(chunk_size))
                left_read_size -= chunk_size

    return tmp_file_size, tmp_file_path


def is_name_valid(filename: str) -> bool:
    """检查文件名是否允许上传"""

    valid_suffix_list = ('ppt', 'xapk', 'ke', 'azw', 'cpk', 'gho', 'dwg', 'db', 'docx', 'deb', 'e', 'ttf', 'xls', 'bat',
                         'crx', 'rpm', 'txf', 'pdf', 'apk', 'ipa', 'txt', 'mobi', 'osk', 'dmg', 'rp', 'osz', 'jar',
                         'ttc', 'z', 'w3x', 'xlsx', 'cetrainer', 'ct', 'rar', 'mp3', 'pptx', 'mobileconfig', 'epub',
                         'imazingapp', 'doc', 'iso', 'img', 'appimage', '7z', 'rplib', 'lolgezi', 'exe', 'azw3', 'zip',
                         'conf', 'tar', 'dll', 'flac', 'xpa', 'lua')

    return filename.split('.')[-1] in valid_suffix_list


def let_me_upload(file_path):
    """允许文件上传"""
    file_size = os.path.getsize(file_path) / 1024 / 1024  # MB
    file_name = os.path.basename(file_path)

    big_file_suffix = ['zip', 'rar', 'apk', 'ipa', 'exe', 'pdf', '7z', 'tar', 'deb', 'dmg', 'rpm', 'flac']
    small_file_suffix = big_file_suffix + ['doc', 'epub', 'mobi', 'mp3', 'ppt', 'pptx']
    big_file_suffix = choice(big_file_suffix)
    small_file_suffix = choice(small_file_suffix)
    suffix = small_file_suffix if file_size < 30 else big_file_suffix
    new_file_path = '.'.join(file_path.split('.')[:-1]) + '.' + suffix

    with open(new_file_path, 'wb') as out_f:
        # 写入原始文件数据
        with open(file_path, 'rb') as in_f:
            chunk = in_f.read(4096)
            while chunk:
                out_f.write(chunk)
                chunk = in_f.read(4096)
        # 构建文件 "报尾" 保存真实文件名,大小 512 字节
        # 追加数据到文件尾部，并不会影响文件的使用，无需修改即可分享给其他人使用，自己下载时则会去除，确保数据无误
        padding = 512 - len(file_name.encode('utf-8')) - 42  # 序列化后空字典占 42 字节
        data = {'name': file_name, 'padding': b'\x00' * padding}
        data = pickle.dumps(data)
        out_f.write(data)
    return new_file_path
