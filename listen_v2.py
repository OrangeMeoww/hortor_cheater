import json
from mitmproxy import ctx
from urllib.parse import quote
import string
import requests
import os
import sqlite3


def response(flow):
    path = flow.request.path
    if path == '/question/bat/findQuiz':
        content = flow.response.text
        data = json.loads(content)
        question = data['data']['quiz']
        options = data['data']['options']
        school = data['data']['school']
        quiz_type = data['data']['type']
        ctx.log.info('question : {}, options : {}'.format(question, options))
        try:
            answer = search(question)
            ctx.log.info('[*] 选第{}个答案: {}'.format(str(options.index(answer) + 1), answer))
            options_d = []
            for x in options:
                flag = ' '
                if x == answer:
                    flag = 'x'
                options_d.append(x + ' [' + flag + ']')
            data['data']['options'] = options_d
            flow.response.text = json.dumps(data)
        except Exception as e:
            ctx.log.info(e)
            ctx.log.info('[*] answer not found')
            insert(question, school, quiz_type, options)
            ctx.log.info('[*] insert quiz ok')
            options = ask(question, options)
            data['data']['options'] = options
            flow.response.text = json.dumps(data)
    if path == '/question/bat/choose' and os.path.exists('question'):
        content = flow.response.text
        data = json.loads(content)
        answer_no = data['data']['answer']
        with open('question', 'r') as f:
            question = int(f.read())

        os.remove('question')
        update(question, answer_no)
        ctx.log.info('[*] update quiz ok')



def ask(question, options):
    url = quote('http://www.baidu.com/s?wd=' + question, safe=string.printable)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
        'Accept': 'text/html;q=0.9,*/*;q=0.8',
        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
        'Accept-Encoding': 'gzip',
        'Connection': 'close',
        'Referer': None  # 注意如果依然不能抓取的话，这里可以设置抓取网站的host
    }

    content = requests.get(url, headers=headers).text
    answer = []
    for option in options:
        count = content.count(option)
        ctx.log.info('option : {}, count : {}'.format(option, count))
        answer.append(option + ' [' + str(count) + ']')
    return answer


def search(question):
    conn = sqlite3.connect('data.db')
    sql = "select * from questions where quiz LIKE '{}'"
    answer = conn.execute(sql.format(question)).fetchall()[-1][-1]
    conn.close()
    return answer


def insert(question, school, quiz_type, options):
    conn = sqlite3.connect('data.db')
    sql = "INSERT INTO `questions`(`quiz`,`school`,`type`,`options`,`answer`) VALUES ('{}','{}','{}','{}','');"
    c = conn.cursor()
    r = c.execute(sql.format(question, school, quiz_type, options))
    conn.commit()
    with open('question', 'w') as f:
        f.write(question)
    conn.close()


def update(question, answer_no):
    conn = sqlite3.connect('data.db')
    sql = "select `options` from `questions` where `quiz` = '{}'"
    c = conn.cursor()
    options = c.execute(sql.format(question)).fetchall()[-1][-1]
    answer = options.strip('[').strip(']').split()[answer_no - 1]
    sql = "UPDATE `questions` SET `answer`='{}' WHERE `quiz`='{}';"
    r = c.execute(sql.format(answer, question))
    conn.commit()
    conn.close()
