from typing import Optional

from dingtalkchatbot.chatbot import DingtalkChatbot
import requests
import json
import time
import configparser
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr
import smtplib
from NodeInfo import NodeInfo
from NodeDiff import NodeDiff


def alaya_nodes():
    url = cf.get('app', 'provider')
    payload = '{"jsonrpc":"2.0","method":"platon_call","params":[{"data": "0xc48382044e", ' \
              '"to": "atp1zqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqzfyslg3"}, "latest"],"id":67}'
    headers = {
        'content-type': 'application/json'
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    result = response.json()["result"]
    return bytes.fromhex(result[2:]).decode("utf-8")


def send_msg(msg: str, ding_address=None, mail_address=None, mail_name=None):
    if dingding_enable:
        xiaoding.send_text(msg, at_mobiles=ding_address)

    if mail_enable:
        mail_msg = MIMEText(msg, 'plain', 'utf-8')
        mail_msg['From'] = msg_address
        if mail_address is None:
            mail_msg['To'] = msg_address
        else:
            mail_msg['To'] = formataddr((Header(mail_name, 'utf-8').encode(), mail_address))
        mail_msg['Subject'] = Header(subject, 'utf-8').encode()

        server.connect(server_host, port)
        server.login(address, password)
        if mail_address is None:
            server.sendmail(address, [address], mail_msg.as_string())
        else:
            server.sendmail(address, [mail_address], mail_msg.as_string())
        server.quit()


def get_diff(_node: NodeInfo, _item: dict, _rank: int) -> (Optional[NodeDiff]):
    if _node.id.lower() != _item["NodeId"].lower():
        return None
    node_diff = NodeDiff(_node.id, _node.dingding, _node.mail)
    node_diff.shares_diff = int(_item["Shares"], 16) - _node.shares
    node_diff.status = _item["Status"]
    node_diff.rank_diff = i + 1 - _node.rank
    return node_diff


def init_node(_node: NodeInfo, _item: dict, _rank: int) -> Optional[NodeInfo]:
    if _node.id.lower() != _item["NodeId"].lower():
        return None
    _node.rank = _rank + 1
    _node.name = _item["NodeName"]
    _node.shares = int(_item["Shares"], 16)
    return _node


cf = configparser.ConfigParser()
cf.read("config.ini", encoding='utf-8')
interval = int(cf.get('app', 'interval'))
dingding_enable = False
mail_enable = False

if cf.get('dingding', 'enable').lower() == 'true':
    dingding_enable = True
    webhook = cf.get('dingding', 'webhook')
    secret = cf.get('dingding', 'secret')
    xiaoding = DingtalkChatbot(webhook, secret=secret)
if cf.get('mail', 'enable').lower() == 'true':
    password = cf.get('mail', 'psd')
    name = cf.get('mail', 'name')
    address = cf.get('mail', 'address')
    msg_address = formataddr((Header(name, 'utf-8').encode(), address))
    server_host = cf.get('mail', 'server')
    pt_str = cf.get('mail', 'port').strip()
    port = 25 if len(pt_str) == 0 else int(pt_str)
    server = smtplib.SMTP(server_host, port)
    subject = cf.get('mail', 'subject')
    mail_enable = True

watching_nodes = {}
time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
with open(cf.get('app', 'node_info_file'), 'r') as f:
    for line in f:
        parts = line.split(',')
        info = NodeInfo(parts[0].strip(), parts[1].strip(), parts[2].strip())
        watching_nodes[info.id] = info
        print(time_str, info.id, info.dingding, info.mail)
send_msg('Alaya预警正在运行！')
while True:
    res_json = json.loads(alaya_nodes())
    node_length = len(res_json["Ret"])
    if res_json["Code"] == 0 and node_length > 0:
        time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        print(time_str, "节点总数：{}".format(node_length))
        for i in range(node_length):
            item = res_json["Ret"][i]
            node_id = item["NodeId"].lower()
            if node_id.startswith('0x'):
                node_id = node_id[2:]
            node = watching_nodes.get(node_id)
            if node is None:
                continue

            if node.rank == 0:
                """节点信息没有初始化"""
                ret_node = init_node(node, item, i)
                if ret_node is not None:
                    watching_nodes[item["NodeId"]] = ret_node
                continue

            diff = get_diff(node, item, i)
            if diff is None:
                continue

            shares_increase_threshold = int(cf.get('alert_type', 'shares_increase_threshold')) * 10**18
            shares_reduce_threshold = int(cf.get('alert_type', 'shares_reduce_threshold')) * 10**18
            if 0 < shares_increase_threshold <= diff.shares_diff:
                send_msg("你的节点{}质押加被委托量正在上升，现在质押加被委托量为{:.3f}ATP！"
                         .format(node.name, (node.shares+diff.shares_diff) / 10 ** 18),
                         ding_address=[node.dingding], mail_address=node.mail, mail_name=node.name)
                node.shares = int(item["Shares"], 16)
            elif abs(diff.shares_diff) >= shares_reduce_threshold > 0 > diff.shares_diff:
                send_msg("你的节点{}质押加被委托量正在降低，现在质押加被委托量为{:.3f}ATP！"
                         .format(node.name, (node.shares+diff.shares_diff) / 10**18),
                         ding_address=[node.dingding], mail_address=node.mail, mail_name=node.name)
                node.shares = int(item["Shares"], 16)
            # 排名上升达到阈值进行提醒，-1表示永不提醒
            rank_increase_threshold = int(cf.get('alert_type', 'rank_increase_threshold'))
            # 排名下降达到阈值后进行提醒，-1为不提醒
            rank_reduce_threshold = int(cf.get('alert_type', 'rank_reduce_threshold'))
            if diff.rank_diff >= rank_increase_threshold > 0:
                send_msg("你的节点{}排名正在升高，现在的排名为{}！".format(node.name, node.rank),
                         ding_address=[node.dingding], mail_address=node.mail, mail_name=node.name)
                node.rank = i + 1
            elif abs(diff.rank_diff) >= rank_reduce_threshold > 0 > diff.rank_diff:
                send_msg("你的节点{}排名正在下降，现在的排名为{}！".format(node.name, node.rank),
                         ding_address=[node.dingding], mail_address=node.mail, mail_name=node.name)
                node.rank = i + 1
            # 排名达到阈值或阈值之后进行提醒，-1为不提醒
            rank_threshold = int(cf.get('alert_type', 'rank_threshold'))
            if node.rank >= rank_threshold > 0:
                send_msg("你的节点{}排名出现异常，现在的排名为{}，请及时处理！".format(node.name, node.rank),
                         ding_address=[node.dingding], mail_address=node.mail, mail_name=node.name)
                node.rank = i + 1
            # 是否对状态改变进行提醒，true为提醒，false为不提醒
            status_enable = cf.get('alert_type', 'status_enable')
            if status_enable.lower() == 'true' and diff.status > 0:
                send_msg("你的节点{}状态有异常，请关注！".format(node.name),
                         ding_address=[node.dingding], mail_address=node.mail, mail_name=node.name)
    time.sleep(interval)
