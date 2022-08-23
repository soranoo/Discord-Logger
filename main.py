from datetime import datetime
import websocket # websocket-client
import json
import threading
import time
import os
import pyfiglet

from rich import print, traceback
from datetime import datetime

from src import config, project_main_directory
from src import log, add_logging_level, log_levels, Colorcode # log
from src import subscribe, unsubscribe, post_event # event system
from src import db_path, db_write, db_read, db_create_table, datetime_to_db_date # database

traceback.install()
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))) # get current directory

# ---------------* Common *---------------
discord_webSocket = config.get("discord_webSocket")
discord_user_token = config.get("discord_user_token")
auto_reconnect = config.get("auto_reconnect")
display_server_id = config.get("display_server_id")
display_channel_id = config.get("display_channel_id")
display_user_id = config.get("display_user_id")
define_server = config.get("define_server")
define_channel = config.get("define_channel")

enable_server_whitelist = config.get("enable_server_whitelist")
enable_channel_whitelist = config.get("enable_channel_whitelist")
whitelist_sever = config.get("whitelist_sever")
whitelist_channel = config.get("whitelist_channel")
enable_server_blacklist = config.get("enable_server_blacklist")
enable_channel_blacklist = config.get("enable_channel_blacklist")
blacklist_sever = config.get("blacklist_sever")
blacklist_channel = config.get("blacklist_channel")

db_table = "logger"

class clog:
    def error(ctx):
        log.error(f"{Colorcode.red}{ctx}{Colorcode.reset}")
    def warning(ctx):
        log.warning(f"{Colorcode.yellow}{ctx}{Colorcode.reset}")

# ---------------* Main *---------------
# welcome message
print(pyfiglet.figlet_format("Discord  Logger"))

add_logging_level("DISCORD", log_levels.DISCORD, "white")
add_logging_level("MSG", log_levels.MSG, "cyan")
add_logging_level("EDIT", log_levels.EDIT, "yellow")
add_logging_level("DELETE", log_levels.DELETE, "red")
add_logging_level("EMBED", log_levels.EMBED, "cyan")

db_create_table(db_table, ["message_id", "server_id", "channel_id", "user_id", "username", "content"])

def get_current_timestamp():
    return datetime.now().timestamp()

def send_json_request(ws, request):
    ws.send(json.dumps(request))

def heartbeat(ws, interval = 40, loop = False):
    stopFlag = False
    if loop:
        def stopHeartbeat(stop):
            return stop
        stopFlag = subscribe("stop_heartbeat", stopHeartbeat)
    while True:
        heartbeatJSON = {
            "op": 1,
            "d": "null"
        }
        try:
            send_json_request(ws, heartbeatJSON)
            log.debug(f"Heartbeat Sent~")
        except Exception as err:
            clog.error(f"Heartbeat sent failed, reason: {err}")
            log.info(f"Heartbeat Stopped")
            break
        if loop and not stopFlag:
            time.sleep(interval)
        else:
            if stopFlag:
                unsubscribe("stop_heartbeat", stopHeartbeat)
            break


def on_message(ws, message):
    json_message = json.loads(message)
    sub = f"{Colorcode.gray}>{Colorcode.reset}"
    try:        
        op_code = json_message["op"] # ref: https://discord.com/developers/docs/topics/opcodes-and-status-codes#gateway-gateway-opcodes
        if op_code == 10:
            log.debug("Initialize heartbeat cycle...")
            heartbeatInterval = (json_message["d"]["heartbeat_interval"]/1000)-1
            log.info(f"Set heartbeat interval to {heartbeatInterval}s.")
            # Start heartbeat cycle
            new_thread = threading.Thread(target=heartbeat, args=[ws, heartbeatInterval, True])
            new_thread.daemon = True
            new_thread.start()
            log.info("Start listening...")
        elif op_code == 6 or op_code == 7:
            reconnect_discord_ws()
        elif op_code == 0:
            event = json_message["d"]
            intent = json_message["t"] # ref: https://discord.com/developers/docs/topics/gateway#gateway-intents
            message_id = event["id"] if "id" in event else None
            username = event["author"]["username"] if "author" in event else Colorcode.gray+"unknown"+Colorcode.reset
            user_id = event["author"]["id"] if "author" in event else Colorcode.gray+"N/A"+Colorcode.reset
            server_id = event["guild_id"] if "guild_id" in event else None
            server_name = None
            if server_id != None:
                for server in define_server:
                    if server_id in server[0]:
                        server_name = server[1][0]
                        break

            channel_id = event["channel_id"] if "channel_id" in event else None
            channel_name = None
            for channel in define_channel:
                if channel_id in channel[0]:
                    channel_name = channel[1][0]
                    break
                if server_id is None:
                    channel_name = "Direct Message"
                    break

            server_tag = f"[{server_name}({server_id})]" if server_name is not None and display_server_id is True and server_id != None else f"[{server_name}]" if server_name is not None and server_id != None else f"[{server_id}]" if display_server_id is True and server_id != None else ""
            channel_tag = f"{channel_name}({channel_id})" if channel_name is not None and display_channel_id is True else f"{channel_name}" if channel_name is not None else f"[{channel_id}]" if display_channel_id is True else ""

            def create_msg_prefix(server_tag = server_tag, channel_tag = channel_tag, username = username, user_id = user_id):
                return f"{server_tag}{' ➜  ' if server_tag != '' else ''}{channel_tag} <{username}{f'({user_id})' if display_user_id else ''}>: "

            msgPrefix = create_msg_prefix()

            def process_content(content:str, join_prefix:bool = True, msg_prefix:str = msgPrefix) -> list:
                multiline_content = ""
                if "\n" in content:
                    multiline_content = content.split("\n")
                    content = Colorcode.gray+"{This is a multiline content vvv }"+Colorcode.reset
                msg = [f"{msg_prefix if join_prefix else ''}{content}"]
                if multiline_content != "":
                    for ctx in multiline_content:
                        msg.append(f"{sub} {ctx}")
                return msg

            def do_log(raw_content: str):
                username = event["author"]["username"] if "author" in event else Colorcode.gray+"unknown"+Colorcode.reset
                if "CREATE" in intent:
                    db_write(db_table, ["date", "type", "message_id", "server_id", "channel_id", "user_id", "username", "content"],
                            [get_current_timestamp(), "new_message", message_id, server_id, user_id, channel_id, username, raw_content])
                    for ctx in process_content(raw_content):
                        log.msg(ctx)
                        
                if "UPDATE" in intent:
                    record = db_read(db_table, ["date", "type", "message_id", "server_id", "channel_id", "user_id", "username", "content"],
                            f"message_id = '{message_id}'")
                    if len(record) > 0:
                        # find the newest record
                        newest_record = record[-1]
                        old_text = newest_record[-1]
                        log.edit(f"{msgPrefix}")
                        log.edit(f"{Colorcode.gray}" + "{FROM}" + f"{Colorcode.reset}")
                        for ctx in process_content(old_text, False):
                            log.edit(ctx)
                        log.edit(f"{Colorcode.gray}" + "{TO}" + f"{Colorcode.reset}")
                        for ctx in process_content(raw_content, False):
                            log.edit(ctx)
                    else:
                        log.edit(f"{msgPrefix}")
                        log.edit(f"{Colorcode.gray}" + "{FROM}" + f"{Colorcode.reset}")
                        log.edit(f"{Colorcode.gray}<NO RECORD FOUND>{Colorcode.reset}")
                        log.edit(f"{Colorcode.gray}" + "{TO}" + f"{Colorcode.reset}")
                        for ctx in process_content(raw_content, False):
                            log.edit(ctx)      
                    db_write(db_table, ["date", "type", "message_id", "server_id", "channel_id", "user_id", "username", "content"],
                            [get_current_timestamp(), "edit_message", message_id, server_id, user_id, channel_id, username, raw_content])
                            
                if "DELETE" in intent:
                    record = db_read(db_table, ["date", "type", "message_id", "server_id", "channel_id", "user_id", "username", "content"],
                            f"message_id = '{message_id}'")
                    if len(record) > 0:
                        # find the newest record
                        newest_record = record[-1]
                        old_text = newest_record[-1]
                        username = newest_record[6]
                        db_write(db_table, ["date", "type", "message_id", "server_id", "channel_id", "user_id", "username", "content"],
                                [get_current_timestamp(), "delete_message", message_id, server_id, user_id, channel_id, username, old_text])
                        for ctx in process_content(old_text, msg_prefix=create_msg_prefix(username=username)):
                            log.delete(ctx)
                    else:
                        log.delete(f"{msgPrefix}{Colorcode.gray}<NO RECORD FOUND>{Colorcode.reset}")
                        db_write(db_table, ["date", "type", "message_id", "server_id", "channel_id", "user_id", "username", "content"],
                                [get_current_timestamp(), "delete_message", message_id, server_id, user_id, channel_id, username, None])

            if "content" in event and event["content"] != "":
                raw_content = event["content"]

                # filter
                if enable_server_whitelist and server_id in whitelist_sever:
                    if (enable_channel_whitelist and channel_id in whitelist_channel) or (enable_channel_blacklist and channel_id not in blacklist_channel) or (enable_channel_whitelist is False and enable_channel_blacklist is False):
                        do_log(raw_content)
                elif server_id is None and ((enable_channel_whitelist and channel_id in whitelist_channel) or (enable_channel_blacklist and channel_id not in blacklist_channel) or (enable_channel_whitelist is False and enable_channel_blacklist is False)):
                    do_log(raw_content)
                # log all messages
                elif enable_server_whitelist is False and enable_channel_whitelist is False and enable_server_blacklist is False and enable_channel_blacklist is False:
                    do_log(raw_content)
            elif "DELETE" in intent:
                do_log(None)
                
            if "embeds" in event:
                embeds = event["embeds"]
                msg = [] if "content" in event and event["content"] != "" else [msgPrefix+Colorcode.gray+"{This is a embed message ⬇⬇⬇⬇ }"+Colorcode.reset] if len(embeds) > 0 else [msgPrefix+Colorcode.gray+"{empty embed message}"+Colorcode.reset]
                for index, embed in enumerate(embeds):
                    for key, value in embed.items():
                        value = str(value).split("\n")
                        if len(value) > 1:
                            msg.append(f"{sub}{key} ➜ {Colorcode.gray}"+"{This is a multiline " + key + " ⬇⬇⬇⬇ }"+Colorcode.reset)
                            for ctx in value:
                                msg.append(f"{sub}{sub} {ctx}")
                        else:
                            msg.append(f"{sub} {key} ➜  {value}")
                    log.debug(f"^embed index {index}")

                # output
                for ctx in msg:
                    log.embed(ctx)

            

    except Exception as err:
        clog.error(err)

def on_error(ws, error):
    clog.error(f"An error has occurred by the websocket, reason: {error}")

def on_close(ws, close_status_code, close_msg):
    log.info(f"### Disconnected ###")
    log.info(f"Status Code: {close_status_code}")
    log.info(f"Close Message: {close_msg}")
    if auto_reconnect:
        try:
            log.info(f"Trying to reconnect...")
            reconnect_discord_ws()
        except Exception as error:
            clog.error(f"Reconnect failed, reason: {error}")

def on_open(ws):
    heartbeat(ws, loop=False)
    login_payload = {
        "op": 2,
        "d": {
            "token": discord_user_token,
            "properties": {
                "$os": "windows",
                "$browser": "chrome",
                "$device": "pc"
            }
        }
    }
    send_json_request(ws, login_payload)

def connect_discord_ws(timeout=-1):
    log.info(f"### Start ###")
    ws = websocket.WebSocketApp(discord_webSocket,
                            on_open = on_open,
                            on_message = on_message,
                            on_error = on_error,
                            on_close = on_close)
    ws.run_forever()

def reconnect_discord_ws():
    post_event("stop_heartbeat", True) # stop current heartbeat cycle
    connect_discord_ws()

if __name__ == "__main__":
    connect_discord_ws()
