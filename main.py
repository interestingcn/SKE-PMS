# !/usr/bin/env python
# -*- coding:utf-8 -*-
# Author:interestingcn01
# LastUpdate:2021.7.28

import json,configparser,time,requests,sys,os
from bs4 import BeautifulSoup

def welcome():
    msg = '''
============================================================
   _____ _  ________      _____  __  __  _____ 
  / ____| |/ /  ____|    |  __ \|  \/  |/ ____|
 | (___ | ' /| |__ ______| |__) | \  / | (___  
  \___ \|  < |  __|______|  ___/| |\/| |\___ \ 
  ____) | . \| |____     | |    | |  | |____) |
 |_____/|_|\_\______|    |_|    |_|  |_|_____/ 
    Personnel monitoring system for SKE 
============================================================                                    
    '''
    print(msg)

def getConfig(category,value):
    config = configparser.ConfigParser()
    try:
        config.read("config.ini", encoding="utf-8-sig")
        return config.get(category, value)
    except:
        print('检查config.ini配置文件是否存在以及是否有权限访问！')
        sys.exit()

# 预备环境文件检测
def checkEnv():
    debugInfo('创建预备环境')
    if os.path.exists(getConfig('SYSTEM','tmpPath')+'/'+getConfig('SYSTEM','dbFile')):
        pass
    else:
        os.makedirs(getConfig('SYSTEM','tmpPath'))
        with open(getConfig('SYSTEM','tmpPath')+'/'+getConfig('SYSTEM','dbFile'),'w') as file:
            file.write('{}')

    if os.path.exists(getConfig('SCREENSHOT','path')):
        pass
    else:
        os.makedirs(getConfig('SCREENSHOT', 'path'))

    if os.path.exists(getConfig('SYSTEM', 'markFile')):
        pass
    else:
        with open(getConfig('SYSTEM', 'markFile'), 'w') as file:
            file.write('')

# 用于提取页面中CSRF信息
def get_CSRF(text):
    csrf = {}
    bs = BeautifulSoup(text, 'lxml')
    # 将隐藏域内容写入表单
    hidden = bs.find_all(type='hidden')
    for i in hidden:
        bs2 = BeautifulSoup(str(i), 'lxml')
        csrf[bs2.input['id']] = bs2.input['value']
    return csrf

def delTdLabel(text,nospace=1):
    if nospace == 1:
        return str(text).replace('<td>', '').replace('</td>', '').replace(' ', '')
    else:
        return str(text).replace('<td>', '').replace('</td>', '')

def displayMsg(text):
    timenow = time.asctime(time.localtime(time.time()))
    msg = f'{timenow} - {str(text)} '
    print(msg)

def debugInfo(text):
    timenow = time.asctime(time.localtime(time.time()))
    msg = f'{timenow} - [DEBUG] -{str(text)} '
    if getConfig('SYSTEM','debug') == '1':
        print(msg)

def resetDbFile():
    with open(getConfig('SYSTEM','tmpPath')+'/'+getConfig('SYSTEM','dbFile'),'w') as file:
        file.write('')
        file.close()
        debugInfo('数据库已重置')

def sendWxMessage(token,content,summary,topicIds=[]):
    url = 'http://wxpusher.zjiecode.com/api/send/message'
    header = {'Content-Type': 'application/json',"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36"}
    data = {"appToken":token,"content":content,"summary":summary,"topicIds": topicIds,"contentType":"1"}
    re = requests.post(url, json.dumps(data),headers=header)
    return json.loads(re.text)['success']

def LibMsg(direction,name,id,dept,type,intime,nowNum):
    # 获取当前服务器时间
    serverTime = time.strftime("%Y/%m/%d  %H:%M:%S", time.localtime())
    if direction == 'in':
        summary = '[ ' + name + ' ] 已进入'+getConfig('SCAN','sence')
        content = f'【入场通知】\n\n姓名：{name}\nID:{id}\n部门:{dept}\n类型:{type}\n进入时间:{intime}\n服务器上报时间:{serverTime}\n当前总计人数:{nowNum}\n'
    elif direction == 'out':
        summary = '[ ' + name + ' ] 已离开'+getConfig('SCAN','sence')
        content = f'【离场通知】\n\n姓名：{name}\nID:{id}\n进入时间:{intime}(已离开)\n服务器上报时间:{serverTime}\n当前总计人数:{nowNum}\n'
    else:
        print('未知状态：请重新定义进出状态 in or out ！')
        exit()
    # 发送微信消息
    wxpusherToken=getConfig('PUSH','wxpusherToken')
    # 将主题ID添加进入列表
    wxpusherTopic=[]
    wxpusherTopic.append(getConfig('PUSH','wxpusherTopic'))
    sendWxMessage(wxpusherToken,content,summary,wxpusherTopic)

    # 登录操作
def getLoginCookies():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36"}
    session = requests.session()
    TargetUrl = getConfig('SKESERVER','address')+'InLibraryReaderInfo.aspx'
    resp = session.get(TargetUrl,headers=headers)
    form_data = get_CSRF(resp.text)
    form_data['Textbox_name1'] = getConfig('SKESERVER','username')
    form_data['TextBox_password'] = getConfig('SKESERVER','password')
    form_data['Button1'] = '确认'
    # 登陆验证操作
    ValidateUrl = getConfig('SKESERVER','address')+'Validate.aspx'
    vaild = session.post(ValidateUrl,form_data,headers=headers)

    if checkLoginStatus(vaild) == 1:
        displayMsg('登陆成功')
        # 注意此处获取cookies为服务器下发cookies时的请求而非任意请求
        cookies = resp.cookies
        return requests.utils.dict_from_cookiejar(cookies)
    else:
        displayMsg('登陆失败')
        input('按回车键退出程序（Enter）')
        exit()

# 检查登录状态
def checkLoginStatus(context):
    bs = BeautifulSoup(context.text, 'lxml')
    res = bs.find_all(text='请输入用户名和密码进行认证')
    if len(res) == 0:
        return 1
    else:
        return 0

def freeTime():
    # 非工作时段清空在场数据库信息
    nowHour = time.strftime("%H", time.localtime())
    if int(nowHour) < int(getConfig('SCAN','freetime')):
        displayMsg('非工作时段！')
        resetDbFile()
        return 1
    else:
        return 0

# 获取人员列表HTML页面
def getInfoContext(cookie):
    # 第二次提交 添加类型部门区域信息
    # 添加目标对象到列表中
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36"}
    TargetUrl = getConfig('SKESERVER','address')+'InLibraryReaderInfo.aspx'
    resp = requests.get(TargetUrl, headers=headers, cookies=cookie)

    # form_data = ''
    # form_data = get_CSRF(resp.text)
    # # 选择正门
    # form_data['ListBox_location_n'] = '1 &'
    # form_data['Button_location_add'] = '>'
    # vaild = requests.post(TargetUrl,form_data,headers=headers,cookies=cookie)
    # 第三次提交 执行统计操作

    # 反馈查询结果到页面
    form_data = get_CSRF(resp.text)
    form_data['button_do'] = '统计'
    return requests.post(TargetUrl, form_data, headers=headers, cookies=cookie)  # 此处包含查询结果

# 本地处理信息并发送消息
def mainWork(context):
    # 信息全部获取完毕，开始本地处理
    bs = BeautifulSoup(context.text, 'lxml')
    dataTable = bs.find_all('table', id='DataGrid1')
    bs = BeautifulSoup(str(dataTable), 'lxml')
    readerList = bs.find_all('tr')
    del readerList[0]  # 删除表头信息

    userInfoList = []  # 在馆全部用户信息列表(处理完毕)
    userIdList = []  # 在馆全部用户卡号 用于消息推送等定位使用

    for tr in readerList:  # 全部用户列表(原始)
        info = tr.find_all('td')
        # [<td>2017xxxxxx</td>, <td>姓名</td>, <td>类型</td>, <td>部门</td>, <td>时间</td>]
        dict = {}
        dict['id'] = delTdLabel(info[0])
        dict['name'] = delTdLabel(info[1])
        dict['type'] = delTdLabel(info[2])
        dict['dept'] = delTdLabel(info[3])
        dict['time'] = delTdLabel(info[4], 0)

        # 填写对应数据组到列表
        userIdList.append(dict['id'])
        userInfoList.append(dict)

    # 统计人员总数量
    reader_num = len(userInfoList)

    # 获取标记列表卡号数据为markList
    markIdList = []
    with open(getConfig('SYSTEM','markFile'), 'r') as file:
        file = file.readlines()
        for i in file:
            markIdList.append(i.replace('\n', ''))

    # 标记卡号与在馆卡号 交集
    markList = list(set(userIdList) & set(markIdList))
    # print(markList)
    # ['2019xxxxxxx']

    # 读取数据库中已在馆人员记录
    with open(getConfig('SYSTEM','tmpPath')+'/'+getConfig('SYSTEM','dbFile'), 'r') as reader_in:
        reader_in = reader_in.read()
        try:
            reader_in = json.loads(reader_in)
            debugInfo('数据库信息已载入')
        except:
            print('列表缺失，待重建')
            pass

        # 数据库中标记在场人员ID列表
        dbIdList = []
        # 将姓名与时间按照预定字符串进行分割
        for i in reader_in:
            reader_in[i] = str(reader_in[i]).split('+-+-+')
            dbIdList.append(i)

    # [入场检测]
    debugInfo('入场检测开始')
    reader_in_now = {}
    # 获取在场标记人员信息
    displayMsg('当前在场关注人员名单：')
    print('====================================')
    for user in userInfoList:
        # user:{'id': 'xxxxxx', 'name': 'xxx', 'type': 'xx', 'dept': 'xxxx', 'time': '2021/7/32 13:28:46'}
        for markId in markList:
            if user['id'] == markId:
                print('ID:' + user['id'])
                print('姓名：' + user['name'])
                # print('部门：' + user['dept'])
                # print('类型：' + user['type'])
                print('时间：' + user['time'])
                print('====================================')
                if user['id'] in dbIdList:
                    pass
                else:
                    if getConfig('PUSH','pushSwitch') == '1':
                        displayMsg('发送入场通知：' + user['name'] + ' - ' + user['dept'])
                        LibMsg('in', user['name'], user['id'], user['dept'], user['type'], user['time'], str(reader_num))
                reader_in_now[user['id']] = str(user['name']) + '+-+-+' + str(user['time'])
                pass

    print('当前在场人数' + str(reader_num))
    print('====================================')
    debugInfo('入场检测结束')
    # [离场检测]
    # 检测已在场列表中人员是否离开
    debugInfo('离场检测开始')
    for readerId in reader_in:
        if readerId in userIdList:
            pass
        else:
            leaveReaderName = reader_in[readerId][0]
            inTime = reader_in[readerId][1]
            if getConfig('PUSH', 'pushSwitch') == '1':
                displayMsg('正在发送离场通知：' + leaveReaderName)
                LibMsg('out', leaveReaderName, readerId, 0, 0, inTime, str(reader_num))
    debugInfo('离场检测结束')
    # 写入已在场人员记录
    debugInfo('更新数据库信息')
    with open(getConfig('SYSTEM','tmpPath')+'/'+getConfig('SYSTEM','dbFile'), 'w') as file:
        file.write(json.dumps(reader_in_now))
    return userInfoList

# 人员快照
def screenShot(userInfoList):
    # 定位时间
    localtime = time.localtime()
    reader_num = len(userInfoList)
    displayMsg('正在进行人员名单快照')
    with open(getConfig('SCREENSHOT','path')+f'/{time.strftime("%Y-%m-%d@%H-%M", localtime)}.txt', 'w') as file:
        file.write('===================================================================================' + '\r\n')
        file.write(getConfig('SCREENSHOT','title') + '\r\n')
        file.write('\r\n')
        file.write('场景： ' + getConfig('SCAN','sence') + '\r\n')
        file.write('采集时间： ' + time.strftime("%Y-%m-%d %H:%M:%S", localtime) + '\r\n')
        file.write('总计人数： ' + str(reader_num) + '\r\n')
        file.write('\r\n')
        file.write(' ID             名称          类型          部门               进入时间' + '\r\n')
        file.write('------------------------------------------------------------------------------------' + '\r\n')
        for i in userInfoList:
            file.write(
                f"{i['id'].ljust(12)}    {i['name'].ljust(8)}    {i['type'].ljust(8)}    {i['dept'].ljust(12)}   {i['time'].ljust(12)} \r\n")
        file.write('\r\n')
        file.write('===================================================================================' + '\r\n')
        file.write('\r\n')
        file.write('\r\n')
        file.write('\r\n')
        displayMsg('已保存人员名单快照')

if __name__ == '__main__':
    # 打印欢迎消息
    welcome()
    checkEnv()
    while True:
        displayMsg('正在尝试登录')
        # 获取登录会话
        cookie = getLoginCookies()

        print('')
        while True:
            # 检查是否处于工作时间
            if freeTime() == 1:
                time.sleep(60)
                continue
            # 进入指定页面 判断登录状态
            context = getInfoContext(cookie)
            if checkLoginStatus(context) == 0:
                displayMsg('登录失效尝试重新登录')
                break
            # 将指定页面内容进行处理
            userInfoList = mainWork(context)

            # 进行人员快照
            localtime = time.localtime()
            min = time.strftime("%M", localtime)
            # 每十分钟进行一次快照保存
            if int(min) % 10 == 0:
                screenShot(userInfoList)

            debugInfo('任务结束')
            time.sleep(int(getConfig('SCAN','sleep')))
            print('')
            print('')
