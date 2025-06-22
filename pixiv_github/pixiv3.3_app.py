import os,re,pixiv_AI
import requests.cookies, time, random
from threading import Thread
from queue import Queue
from multiprocessing import Process, Queue as PQ
from PyQt6.QtWidgets import QApplication,QWidget,QLabel,QVBoxLayout,QHBoxLayout,QFileDialog
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer
from bs4 import BeautifulSoup
from qfluentwidgets import (LineEdit, PrimaryPushButton, FluentIcon as FIF, HyperlinkButton, ToolButton, InfoBar,
                            IndeterminateProgressBar, PopUpAniStackedWidget, NavigationInterface
, SpinBox, PushButton, CardWidget, PrimaryToolButton, ScrollArea)
r"""
pixiv3.3
文件分布:
pixiv_cookies.txt是保存你的cookies的文件
pix_.jpg是图标
pixiv_AI.py是人工客服文件,用的是deepseek的api,不会用自己前往官方文档查询用法
picture文件夹是保存图片默认文件夹
该文件简介:
    WindowDict是主窗口,根据导航栏选项切换副窗口
        MainWindow是实现爬虫的窗口:需传递一个默认ip与一个变化ip队列
        IPSetting是IP切换窗口:需传递一个IP队列,该队列与MainWindow传递的IP队列相同,实现IP更换
        Customer是客服窗口:需要pixiv_AI.py文件,其实这个功能也没什么用,面向客户端的
剩下的功能自行结合代码注释观看
"""

cookiejar = requests.cookies.RequestsCookieJar()
user_agent = r"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0"
with open(fr"{os.getcwd()}\pixiv_cookies.txt","r",encoding="utf-8") as f:
    cookies = f.read()
for cookie in cookies.split(';'):
    a,b = cookie.split('=',1)
    cookiejar.set(a,b)  #设置cookiejar值


def get_url(url,url_queue:Queue,ip:dict[str, str],num:int):    #获取P站图片链接存入队列
    ID = url.split("/")[-1]
    main_url = fr"https://www.pixiv.net/ajax/illust/{ID}/pages?lang=zh"
    response = requests.get(main_url,cookies=cookiejar,headers={"User-Agent":user_agent,"Referer":"https://www.pixiv.net/"},proxies=ip) #Referer检测是否从pixiv官网上爬取
    body = response.json()["body"]
    for urls in body:
        original = urls["urls"]["original"] #获取直连链接
        url_queue.put(original) #将直连网址导入队列
    for i in range(num):  #发送num个停止命令
        url_queue.put(False)


def get_pix(url,path:str,ip:dict[str, str],thread_num:int=15):  #下载图片,根据get_url方法获得图片路径后分别保存图片
    """
    多线程保存图片
    :param url: 链接
    :param path: 保存路径
    :param ip: IP地址
    :param thread_num: 线程数量
    :return: 爬取到的图片
    """
    url_queue = Queue()
    get_url(url,url_queue,ip,thread_num)
    for i in range(thread_num): #创建thread_num个线程
        get_ = TPixiv(url_queue,path,ip)
        get_.start()


class TPixiv(Thread):   #用于下载图片的线程
    def __init__(self,uq:Queue,path:str,ip:dict[str, str]):
        """
        ...
        :param uq: 图片链接队列
        :param path: 保存路径
        :param ip: IP
        """
        super().__init__()
        self.uq = uq
        self.path = path
        self.ip = ip
    def run(self):
        while True:
            url_pix = self.uq.get()
            #检测队列链接是否为False
            if url_pix is False:
                self.uq.task_done()
                break
            self.uq.task_done()
            #爬取图片
            pix = requests.get(url=url_pix,
                               cookies=cookiejar,
                               headers={"User-Agent": user_agent, "Referer": "https://www.pixiv.net/"},
                               proxies=self.ip)  # 启用代理IP
            time.sleep(random.random())
            # name = ''.join(random.choices("0123456789qwertyuiopasdfghjklzxcvbnm", k=10))  # 随机文件名
            name = time.time()
            #保存
            with open(fr"{self.path}\{name}.{url_pix[-3:]}", "wb") as f:
                f.write(pix.content)  # 下载


def put_many_url(queue:PQ): #将列表文件(pix_list.txt)的网页url加入进程爬取队列
    """
    将图片链接加入队列,内置清单
    :param queue: 队列
    :return: None
    """
    #queue是进程链接队列
    with open(fr"{os.getcwd()}\pix_list.txt", "r") as f: #pix_list.txt清单中获取所有想要爬取的网页
        for i in f.readlines():
            queue.put(i.rstrip("\n"))   #书写pix_list.txt时写一个链接空一行


def every_process(queue:PQ,thread_num:int,path:str,ip:dict[str,str]):    #每个进程执行的任务
    while not queue.empty():
        main_url = queue.get()
        get_pix(main_url,path,ip,thread_num)   #获取单个网页中的所有图片


def main_process_pix(ip:str,path:str,process_num:int=5,thread_num:int=5):
    """
    列表爬虫
    :param ip: IP地址
    :param path: 保存路径
    :param process_num: 进程数量
    :param thread_num: 线程数量
    :return: 将爬取的图片保存到保存路径中
    """
    #主进程分配所有任务给子进程
    queue = PQ()    #创建进程爬取队列(存pix_list.txt的内容)
    put_many_url(queue)
    for i in range(process_num):    #分配任务
        p = Process(target=every_process, args=(queue,thread_num,path,ip))
        p.start()
    with open(fr"{os.getcwd()}\pix_list.txt", "w") as f:
        f.write('')



#IP获取
def get_ip(queue:Queue):
    page = random.randint(1,6)
    url = f"http://www.ip3366.net/?stype=1&page={page}"
    response = requests.get(url)
    pattern = r"<td>(.*?)</td>"
    soup = BeautifulSoup(response.text, 'lxml')
    ip_list = []
    for tr in soup.find_all("tr"):
        ip_dict = dict()
        num = 0
        for td in tr.find_all("td"):
            num += 1
            if num == 1:
                ip = re.match(pattern, str(td)).group(1)
                ip_dict["ip"] = ip
            if num == 2:
                port = re.match(pattern, str(td)).group(1)
                ip_dict["port"] = port
            if num == 4:
                type_ = re.match(pattern, str(td)).group(1)
                ip_dict["type"] = type_
            ip_list.append(ip_dict)
            continue
    resout = random.choice(ip_list)
    queue.put(resout)

#---------------------------------------------------------------------------

class MainWindow(QWidget):
    """
    定义主要功能窗口
    """
    def __init__(self,ip,ip_queue:Queue):
        super().__init__()
        self.main_layout = QVBoxLayout()    #主布局
        self.setLayout(self.main_layout)
        self.card_one = CardWidget()    #卡片一：单进程爬虫
        self.card_two = CardWidget()    #卡片二：多进程爬虫
        self.card_three = CardWidget()  #卡片三：爬虫基础设置
        self.main_layout.addWidget(self.card_one)
        self.main_layout.addWidget(self.card_two)
        self.main_layout.addWidget(self.card_three)
        self.first_main_layout = QVBoxLayout(self.card_one) #卡片一主布局
        self.second_main_layout = QVBoxLayout(self.card_two)   #卡片二主布局
        self.third_main_layout = QVBoxLayout(self.card_three)   #卡片三主布局
        self.ip_queue = ip_queue    #IP桥梁
        self.ip = ip   #IP地址
        #启动主功能
        self.interface()
        self.check_ip = QTimer()    #检测ip是否变化的计时器
        self.check_ip.timeout.connect(self.check_ip_queue)
        self.check_ip.start(1200)

    def check_ip_queue(self):   #检测IP桥梁是否有新内容
        if not self.ip_queue.empty():
            self.ip = self.ip_queue.get()

    def interface(self):
        """
        实现主功能
        :return:None
        """
        #-------------card_one-------------------
        #标题与图片
        first_title = QLabel("用于爬取pixiv的图片")
        first_title.setStyleSheet("color:#0abba9")
        self.first_main_layout.addWidget(first_title, stretch=1)
        #打开pixiv网址链接
        part_one_layout = QHBoxLayout()
        part_one_label = QLabel("打开链接:")
        part_one_linkbutton = HyperlinkButton(FIF.CAR,"https://www.pixiv.net/","pixiv网址")
        part_one_layout.addWidget(part_one_label)
        part_one_layout.addWidget(part_one_linkbutton)
        part_one_layout.addStretch()
        self.first_main_layout.addLayout(part_one_layout, stretch=3)
        #输入插画网址
        part_two_layout = QHBoxLayout()
        self.url_edit = LineEdit()
        self.url_edit.setPlaceholderText("输入pixiv插画url...")
        self.get_button = PrimaryPushButton("爬取资源")
        self.get_button.clicked.connect(self.get_pixiv)
        part_two_layout.addWidget(self.url_edit)
        part_two_layout.addWidget(self.get_button)
        part_two_layout.addStretch()
        self.first_main_layout.addLayout(part_two_layout, stretch=3)
        #设置线程数量
        setting_thread_number_layout = QHBoxLayout()
        setting_thread_label = QLabel("输入启用线程数量:")
        setting_thread_number_layout.addWidget(setting_thread_label)
        self.setting_thread_edit = SpinBox()
        self.setting_thread_edit.setRange(1,50)
        self.setting_thread_edit.setValue(15)
        setting_thread_number_layout.addWidget(self.setting_thread_edit)
        note = QLabel("注释:线程越多处理的数据越多,但是封号风险也会随之增大")
        note.setStyleSheet("color:grey")
        setting_thread_number_layout.addWidget(note)
        setting_thread_number_layout.addStretch(1)
        self.first_main_layout.addLayout(setting_thread_number_layout, stretch=2)
        #提示
        prompt = QLabel("爬虫有封号风险,谨慎爬取\nurl输入插画网页网址\n下载有延迟,显示下载成功后可能并不会那么快刷新出图片")
        prompt.setStyleSheet("color:red")
        self.first_main_layout.addWidget(prompt)

        # -------------card_two-------------------
        #标题
        second_title = QLabel("分布式爬取pixiv插画")
        second_title.setStyleSheet("color:#0abba9")
        self.second_main_layout.addWidget(second_title)
        #打开清单
        card_part_two_layout = QHBoxLayout()
        self.second_main_layout.addLayout(card_part_two_layout, stretch=1)
        open_list_label = QLabel("修改爬虫清单:")
        card_part_two_layout.addWidget(open_list_label)
        self.request_list_open_button = PrimaryPushButton(FIF.DICTIONARY_ADD,"打开清单")
        self.request_list_open_button.clicked.connect(self.open_get_list)
        self.request_list_open_button.setFixedWidth(200)
        card_part_two_layout.addWidget(self.request_list_open_button)
        card_part_two_layout.addStretch(1)
        #开始爬虫
        card_part_three_layout = QHBoxLayout()
        self.second_main_layout.addLayout(card_part_three_layout, stretch=1)
        start_get_list_label = QLabel("爬取清单内容:")
        card_part_three_layout.addWidget(start_get_list_label)
        self.get_list = PrimaryPushButton(FIF.BUS,"爬取清单")
        self.get_list.clicked.connect(self.process_get_pixiv)
        card_part_three_layout.addWidget(self.get_list)
        card_part_three_layout.addStretch(1)
        #修改爬虫进程与线程
        setting_thread_and_process_layout = QHBoxLayout()
        setting_thread_and_process_label_thread = QLabel("输入启用线程数量:")
        setting_thread_and_process_layout.addWidget(setting_thread_and_process_label_thread)
        self.setting_thread_and_process_the_thread = SpinBox()
        self.setting_thread_and_process_the_thread.setRange(1, 50)
        self.setting_thread_and_process_the_thread.setValue(15)
        setting_thread_and_process_layout.addWidget(self.setting_thread_and_process_the_thread)
        setting_thread_and_process_layout.addStretch(1)
        setting_thread_and_process_label_process = QLabel("输入启用进程数量:")
        setting_thread_and_process_layout.addWidget(setting_thread_and_process_label_process)
        self.setting_thread_and_process_the_process = SpinBox()
        self.setting_thread_and_process_the_process.setRange(1, 50)
        self.setting_thread_and_process_the_process.setValue(5)
        setting_thread_and_process_layout.addWidget(self.setting_thread_and_process_the_process)
        setting_thread_and_process_layout.addStretch(1)
        self.second_main_layout.addLayout(setting_thread_and_process_layout)
        #提示
        prompt_two = QLabel("列表爬虫封号可能性更大,列表中要求一行只输入一个链接")
        prompt_two.setStyleSheet("color:red")
        self.second_main_layout.addWidget(prompt_two)

        #-------------card_third-------------------
        # 标题
        third_title = QLabel("pixiv爬虫基本设置")
        third_title.setStyleSheet("color:#0abba9")
        self.third_main_layout.addWidget(third_title)
        # 选择保存路径
        part_three_layout = QHBoxLayout()
        choice_label = QLabel("选择保存图片路径:")
        self.choice_edit = LineEdit()
        self.choice_edit.setFixedWidth(300)
        self.choice_edit.setText(fr"{os.getcwd()}\picture")  # 设置图片存储路径
        self.choice_edit.setPlaceholderText("请选择保存路径...")
        self.choice_button = ToolButton(FIF.FOLDER)
        self.choice_button.clicked.connect(self.file_)
        part_three_layout.addWidget(choice_label)
        part_three_layout.addWidget(self.choice_edit)
        part_three_layout.addWidget(self.choice_button)
        part_three_layout.addStretch()
        self.third_main_layout.addLayout(part_three_layout, stretch=3)
        # 打开配置文件
        part_four_layout = QHBoxLayout()
        message = QLabel("打开配置文件:")
        part_four_layout.addWidget(message)
        open_setting_file_button = PushButton("配置文件")
        open_setting_file_button.clicked.connect(self.open_setting_file)
        part_four_layout.addWidget(open_setting_file_button)
        part_four_layout.addStretch(1)
        self.third_main_layout.addLayout(part_four_layout, stretch=1)
        # 打开保存文件
        part_five_layout = QHBoxLayout()
        save_message = QLabel("打开保存路径:")
        part_five_layout.addWidget(save_message)
        open_save_path_button = PushButton("打开保存图片文件")
        open_save_path_button.clicked.connect(self.open_save_file)
        part_five_layout.addWidget(open_save_path_button)
        part_five_layout.addStretch(1)
        self.third_main_layout.addLayout(part_five_layout, stretch=2)

        # -------------功能页面-------------------

    def open_get_list(self):    #打开下载清单
        os.startfile(fr"{os.getcwd()}\pix_list.txt")

    def open_save_file(self):   #打开保存文件夹
        os.startfile(self.choice_edit.text())

    def open_setting_file(self):    #打开配置文件
        os.startfile(fr"{os.getcwd()}/pixiv_cookies.txt")    #配置文件目录

    def process_get_pixiv(self):    #列表爬虫下载
        # main_process_pix(self.ip,self.choice_edit.text(),5,15)
        self.thread_many = Thread(target=main_process_pix, args=(self.ip,self.choice_edit.text(),self.setting_thread_and_process_the_process.value(),self.setting_thread_and_process_the_thread.value()))
        self.thread_many.start()
        self.timer = QTimer()  # 创建计时器
        self.timer.timeout.connect(self.thread_is_alive_two)
        self.timer.start()
        self.progress_bar = IndeterminateProgressBar()  # 创建进度条
        self.second_main_layout.addWidget(self.progress_bar, stretch=1)

    def file_(self):    #选择保存插画路径
        files = QFileDialog(self).getExistingDirectory()
        if files:
            self.choice_edit.setText(files)

    def get_pixiv(self):    #单一网站爬虫下载管理
        self.info_layout = QVBoxLayout()
        self.first_main_layout.addLayout(self.info_layout, stretch=1)
        if self.choice_edit.text() and os.path.exists(self.choice_edit.text()):
            if self.url_edit.text():

                self.progress_bar = IndeterminateProgressBar()    #创建进度条
                self.first_main_layout.addWidget(self.progress_bar, stretch=1)

                url = self.url_edit.text()
                path = self.choice_edit.text()
                self.thread = T1(url, path, self.setting_thread_edit.value(),self.ip)
                self.thread.start()

                self.timer = QTimer()    #创建下载进度计时器
                self.timer.timeout.connect(self.thread_is_alive)
                self.timer.start()

            else:
                error = InfoBar.error("下载错误", "没有填写插画url",duration=1500)
                self.info_layout.addWidget(error)
        else:
            error = InfoBar.error("下载错误","没有填写保存图片路径/路径不存在/IP可能已经失效",duration=1500)
            self.info_layout.addWidget(error)

    def thread_is_alive(self):  #检验下载线程是否存在
        if not self.thread.is_alive():
            self.progress_bar.deleteLater()
            success = InfoBar.success("下载", "下载成功", duration=2500)
            self.info_layout.addWidget(success)
            self.url_edit.clear()
            self.timer.stop()

    def thread_is_alive_two(self):  #检验下载线程是否存在
        if not self.thread_many.is_alive():
            success = InfoBar.success("下载", "下载成功", duration=2500)
            self.second_main_layout.addWidget(success)
            self.progress_bar.deleteLater()
            self.timer.stop()


class T1(Thread):   #下载图片线程
    def __init__(self, url, path, thread_number,ip):
        super().__init__()
        self.url = url
        self.path = path
        self.thread_number = thread_number
        self.ip = ip
    def run(self):
        get_pix(self.url,self.path,self.ip,self.thread_number) #IP设置可更改

#---------------------------------------------------------------------------

class IPSetting(QWidget):   #IP更换窗口
    def __init__(self,ip_queue:Queue):
        super().__init__()
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.ip_queue = ip_queue

        #题头
        statement = QLabel("更换代理IP:")
        statement.setStyleSheet("color:#0fcdba")
        self.main_layout.addWidget(statement)
        #输入IP地址
        part_one_layout = QHBoxLayout()
        ip_label = QLabel("IP:")
        self.ip_edit = LineEdit()
        self.ip_edit.setFixedWidth(200)
        self.ip_edit.setPlaceholderText("输入IP地址...")
        self.ip_edit.setText("47.119.164.33")
        part_one_layout.addWidget(ip_label)
        part_one_layout.addWidget(self.ip_edit)
        part_one_layout.addStretch(1)
        self.main_layout.addLayout(part_one_layout)
        #输入端口号
        part_two_layout = QHBoxLayout()
        port_label = QLabel("端口号:")
        self.port_edit = LineEdit()
        self.port_edit.setFixedWidth(200)
        self.port_edit.setPlaceholderText("输入端口号...")
        self.port_edit.setText("8081")
        part_two_layout.addWidget(port_label)
        part_two_layout.addWidget(self.port_edit)
        part_two_layout.addStretch(1)
        self.main_layout.addLayout(part_two_layout)
        #输入类型
        part_three_layout = QHBoxLayout()
        type_label = QLabel("类型:")
        self.type_edit = LineEdit()
        self.type_edit.setFixedWidth(200)
        self.type_edit.setPlaceholderText("输入IP地址...")
        self.type_edit.setText("http")
        part_three_layout.addWidget(type_label)
        part_three_layout.addWidget(self.type_edit)
        part_three_layout.addStretch(1)
        self.main_layout.addLayout(part_three_layout)
        #一键更换IP
        part_four_layout = QHBoxLayout()
        update_ip_label = QLabel("一键更换IP:")
        update_ip_button = PrimaryPushButton("更换随机IP")
        update_ip_button.clicked.connect(self.one_click_ip_switching)
        part_four_layout.addWidget(update_ip_label)
        part_four_layout.addWidget(update_ip_button)
        part_four_layout.addStretch(1)
        self.main_layout.addLayout(part_four_layout)
        #确认切换
        part_five_layout = QHBoxLayout()
        ok_ip_label = QLabel("确认IP更换:")
        ok_ip_button = PrimaryPushButton("确认更换")
        ok_ip_button.clicked.connect(self.ok_ip)
        part_five_layout.addWidget(ok_ip_label)
        part_five_layout.addWidget(ok_ip_button)
        part_five_layout.addStretch(1)
        self.main_layout.addLayout(part_five_layout)
        #提示
        prompt = QLabel("一键切换IP功能只存在于软件中内置的切换IP网址还存在时才能使用")
        prompt.setStyleSheet("color:red")
        self.main_layout.addWidget(prompt)

        self.main_layout.addStretch(1)

    def one_click_ip_switching(self):   #一键切换IP功能
        # ip_content = get_ip()
        self.request_queue = Queue() #请求后消息队列
        run_get_ip = Thread(target=get_ip,args=(self.request_queue,))
        run_get_ip.start()
        self.request_wait = QTimer()
        self.request_wait.timeout.connect(self.process_message)
        self.request_wait.start(900)

    def process_message(self):  #计时器检测请求
        if not self.request_queue.empty():
            ip_content = self.request_queue.get()
            self.ip_edit.setText(ip_content['ip'])
            self.port_edit.setText(ip_content['port'])
            self.type_edit.setText(ip_content['type'].lower())
            self.request_wait.stop()

    def ok_ip(self):    #正式更换IP
        ip = self.ip_edit.text()
        port = self.port_edit.text()
        type_ = self.type_edit.text().lower()
        all_ip_content = fr"{type_}://{ip}:{port}"
        self.proxies = {type_: all_ip_content}
        self.ip_queue.put(self.proxies)
        successful_put_ip = InfoBar.success("确认ID","ID保存成功",duration=1500)
        self.main_layout.addWidget(successful_put_ip)

#---------------------------------------------------------------------------

class Customer(QWidget):
    """
    客服页面的内容
    """
    def __init__(self):
        super().__init__()
        c_layout = QVBoxLayout()
        self.setLayout(c_layout)
        #主页面
        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        c_layout.addWidget(scroll)
        self.son = QWidget()
        self.son_layout = QVBoxLayout()
        self.son.setLayout(self.son_layout)
        scroll.setWidget(self.son)
        #输入框
        c_edit_layout = QHBoxLayout()
        c_layout.addLayout(c_edit_layout)
        self.ai_edit = LineEdit()
        self.ai_edit.setPlaceholderText("询问客服的内容...")
        self.ai_edit.editingFinished.connect(self.user_send)
        self.send = PrimaryToolButton(FIF.SEND)
        self.send.clicked.connect(self.user_send)
        c_edit_layout.addWidget(self.ai_edit)
        c_edit_layout.addWidget(self.send)

    def user_send(self):
        """
        用户输入显示对话框
        :return: None
        """
        send_message = self.ai_edit.text()
        self.ai_edit.clear()
        user_message = QLabel(send_message)
        user_message.setStyleSheet("background-color:#7bda0f;border-radius:10px;padding:5px;")
        user_layout = QHBoxLayout()
        user_layout.addStretch(1)
        user_layout.addWidget(user_message,stretch=3)
        self.son_layout.addLayout(user_layout)
        self.ai_queue = Queue()
        self.ai_send(send_message)
        self.receive_ai_message_timer = QTimer()
        self.receive_ai_message_timer.timeout.connect(self.receive_ai_message)
        self.receive_ai_message_timer.start(900)

    def ai_send(self,talk):
        """
        AI输入显示对话框
        :param talk: 用户输入的信息
        :return: AI的回话
        """
        ai = Ai(talk,self.ai_queue)
        ai.start()

    def receive_ai_message(self):
        """
        检测AI发来的消息
        :return: 页面中AI的控件消息
        """
        if not self.ai_queue.empty():
            ai_message = QLabel(self.ai_queue.get())
            ai_message.setStyleSheet("background-color:#0fdac5;border-radius:10px;padding:5px;")
            ai_layout = QHBoxLayout()
            ai_layout.addWidget(ai_message, stretch=3)
            ai_layout.addStretch(1)
            self.son_layout.addLayout(ai_layout)
            self.receive_ai_message_timer.stop()

class Ai(Thread):
    """
    AI处理数据的线程
    """
    def __init__(self, talk:str, q:Queue):
        super().__init__()
        self.q = q
        self.talk = talk
    def run(self):
        #获取AI回话加入队列
        ai = pixiv_AI.deepseek(self.talk)
        self.q.put(ai)

#---------------------------------------------------------------------------

class WindowDict(QWidget):  #软件主窗口
    def __init__(self):
        super().__init__()
        self.resize(650, 600)
        self.setMaximumSize(650, 600)
        self.setMinimumSize(650, 600)
        self.ip_queue = Queue() #MainWindow与IPSetting的IP传递桥梁
        icon = QIcon(fr"{os.getcwd()}\pix_.jpg")  # 设置图片路径
        self.setWindowIcon(icon)
        self.setWindowTitle("pixiv")
        self.proxies = {"http":"http://47.108.220.186:3128"}  #默认IP(代理IP及时更换)
        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)
        self.navigation = NavigationInterface() #导航栏
        self.navigation.addItem("0",FIF.HOME,"pixiv爬虫",lambda : self.stack.setCurrentIndex(0))
        self.navigation.addItem("1", FIF.UPDATE, "IP更换",lambda : self.stack.setCurrentIndex(1))
        self.navigation.addItem("2",FIF.ROBOT,"客服",lambda : self.stack.setCurrentIndex(2))
        self.navigation.setCurrentItem("0")
        self.main_layout.addWidget(self.navigation)
        self.stack = PopUpAniStackedWidget()    #切换页面实例
        self.main_window = MainWindow(self.proxies,self.ip_queue) #添加主窗口
        self.ip_window = IPSetting(self.ip_queue)    #添加IP设置窗口
        self.ai_window = Customer()
        self.stack.addWidget(self.main_window)
        self.stack.addWidget(self.ip_window)
        self.stack.addWidget(self.ai_window)
        self.main_layout.addWidget(self.stack)

#---------------------------------------------------------------------------

if __name__ == '__main__':
    app = QApplication([])
    window = WindowDict()   #主窗口
    window.show()
    app.exec()