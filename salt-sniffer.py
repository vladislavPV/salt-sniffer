import json, time, datetime, os, fnmatch, sys
import salt.config, salt.utils.event
from multiprocessing import Process
from slacker import Slacker

master_conf = '/etc/salt/master'
if os.getenv("MASTER_CONF"):
    master_conf = os.environ['MASTER_CONF']

slack_msg_limit = 4 # msg per event batch
if os.getenv("SLACK_MSG_LIMIT"):
    slack_msg_limit = int(os.environ["SLACK_MSG_LIMIT"])

slack_channel = '#general'
if os.getenv("SLACK_CHANNEL"):
    slack_channel = os.environ["SLACK_CHANNEL"]

exclude_users, exclude_funs, exclude_args = [], [], []
if os.getenv("EXCLUDE_USERS"):
    exclude_users = os.environ['EXCLUDE_USERS'].split(',')

if os.getenv("EXCLUDE_FUNS"):
    exclude_funs = os.environ['EXCLUDE_FUNS'].split(',')

if os.getenv("EXCLUDE_ARGS"):
    exclude_args = os.environ['EXCLUDE_ARGS'].split(',')

if not os.getenv("SLACK_TOKEN"):
    print 'Environment variable SLACK_TOKEN not set.'
    sys.exit(1)
token = os.environ['SLACK_TOKEN']

slack = Slacker(token)

opts = salt.config.client_config(master_conf)
sevent = salt.utils.event.get_event(
        'master',
        sock_dir=opts['sock_dir'],
        transport=opts['transport'],
        opts=opts)

global_dict = {}

def slack_update(ts, text, color, channel, reply_num):
    attachments = [{
        "color": color,
        "text": text,
        "mrkdwn_in": ["text"]
    }]
    time.sleep(abs(0.2 + float(reply_num)/30))  # add delay to slack msg
    slack.chat.update(channel, ts, '', attachments=attachments)


while True:
    ret = sevent.get_event_noblock()

    # filter useless events
    if ret is None:
        continue
    if "data" not in ret:
        continue
    if "jid" not in ret["data"]:
        continue
    if "fun"  in ret["data"] and ret["data"]["fun"]  in exclude_funs:
        continue
    if "user" in ret["data"] and ret["data"]["user"] in exclude_users:
        continue

    found = False
    if "arg" in ret["data"]:
        for arg in exclude_args:
            if arg in str((ret["data"]["arg"])):
                found = True
                break
    if found:
        continue

    jid = ret["data"]["jid"]
    new_event = fnmatch.fnmatch(ret['tag'], 'salt/job/*/new')
    subsequent_event = fnmatch.fnmatch(ret['tag'], 'salt/job/*/ret/*')

    # print json.dumps(ret, indent=4, sort_keys=True)

    if new_event:
        global_dict[jid] = {}
        global_dict[jid]["event"] = ret["data"]
        global_dict[jid]["errors"] = 0
        global_dict[jid]["reply_num"] = 0
        global_dict[jid]["slack_msg_limit_arr"] = []
        global_dict[jid]["start_date"] = datetime.datetime.now()

        step = len(global_dict[jid]["event"]["minions"]) // slack_msg_limit

        # create array with indexes on which to send slack messages
        i = 0
        while i < slack_msg_limit:
            i += 1
            global_dict[jid]["slack_msg_limit_arr"].append(i * step)

        global_dict[jid]["slack_msg_limit_arr"].append(len(global_dict[jid]["event"]["minions"]))

        text = "*User:* "+global_dict[jid]["event"]["user"]
        text += " *Cmd:* "+str(global_dict[jid]["event"]["fun"])+" "+str(global_dict[jid]["event"]["arg"])
        attachments = [{
            "fallback": "In Progress",
            "color": "#439FE0",
            "text": text,
            "mrkdwn_in": ["text"]
        }]

        reply = slack.chat.post_message(slack_channel, '', attachments=attachments)

        global_dict[jid]["slack_thread_ts"] = reply.body["ts"]
        global_dict[jid]["slack_channel"] = reply.body["channel"]


        text  = "*User:* " + global_dict[jid]["event"]["user"] +"\n"
        text += "*Fun:* " + global_dict[jid]["event"]["fun"] +"\n *Args:* "+str(global_dict[jid]["event"]["arg"]) +"\n"
        text += "*Total/Completed/Errors:* " + str(len(global_dict[jid]["event"]["minions"]))+'/'+str(global_dict[jid]["reply_num"])+'/'+str(global_dict[jid]["errors"])+"\n"
        text += "*Tgt:* "+str(global_dict[jid]["event"]["tgt"])
        attachments = [{
            "fallback": "In Progress",
            "color": "#439FE0",
            "text": text,
            "mrkdwn_in": ["text"]
        }]
        reply = slack.chat.post_message(slack_channel, '', attachments=attachments, thread_ts=global_dict[jid]["slack_thread_ts"])
        global_dict[jid]["slack_ts"] = reply.body["ts"]

    if subsequent_event:

        if jid in global_dict:
            msgs = []
            global_dict[jid]["reply_num"] += 1

            if "retcode" in ret["data"] and ret["data"]["retcode"] != 0:
                global_dict[jid]["errors"] += 1

            if global_dict[jid]["reply_num"] not in global_dict[jid]["slack_msg_limit_arr"]:
                continue

            text  = "*User:* " + global_dict[jid]["event"]["user"] +"\n"
            text += "*Fun:* " + global_dict[jid]["event"]["fun"] +"\n *Args:* "+str(global_dict[jid]["event"]["arg"]) +"\n"
            text += "*Total/Completed/Errors:* " + str(len(global_dict[jid]["event"]["minions"]))+'/'+str(global_dict[jid]["reply_num"])+'/'+str(global_dict[jid]["errors"])+"\n"
            text += "*Tgt:* "+str(global_dict[jid]["event"]["tgt"])
            msgs.append({
                "ts":    global_dict[jid]["slack_ts"],
                "text":  text,
                "color": "#439FE0" if global_dict[jid]["errors"] == 0 else "danger",
                "channel": global_dict[jid]["slack_channel"],
                "reply_num": global_dict[jid]["reply_num"]
            })

            if global_dict[jid]["reply_num"] == len(global_dict[jid]["event"]["minions"]):
                time_spent = round((datetime.datetime.now() - global_dict[jid]["start_date"]).total_seconds(), 1)
                msgs[0]["color"] = "good" if global_dict[jid]["errors"] == 0 else "danger"
                msgs.append({
                    "text": "*User:* "+global_dict[jid]["event"]["user"]+" *Cmd:* "+str(global_dict[jid]["event"]["fun"])+" "+str(global_dict[jid]["event"]["arg"])+" *Time:* "+str(time_spent)+" sec",
                    "color": "good" if global_dict[jid]["errors"] == 0 else "danger",
                    "ts": global_dict[jid]["slack_thread_ts"],
                    "channel": global_dict[jid]["slack_channel"],
                    "reply_num": global_dict[jid]["reply_num"]
                })
                del global_dict[jid]

            if msgs != []:
                for msg in msgs:
                    p = Process(
                        target=slack_update,
                        args=(msg["ts"], msg["text"], msg["color"], msg["channel"], msg["reply_num"])
                    )
                    p.start()

