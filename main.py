import toml
import websocket # websocket-client
import json
import threading
import time

from rich import print, traceback

from src.logger import log, Colorcode
from src import eventSystem

traceback.install()

# ---------------* Common *---------------
config = toml.load("config.toml")
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

class clog:
    def error(ctx):
        log.error(f"{Colorcode.red}{ctx}{Colorcode.reset}")
    def warning(ctx):
        log.warning(f"{Colorcode.yellow}{ctx}{Colorcode.reset}")

# ---------------* Store Message *---------------
storeMessages = [
]

# ---------------* Main *---------------
def send_json_request(ws, request):
    ws.send(json.dumps(request))

def heartbeat(ws, interval = 40, loop = False):
    stopFlag = False
    if loop:
        def stopHeartbeat(stop):
            return stop
        stopFlag = eventSystem.subscribe("stop_heartbeat", stopHeartbeat)
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
                eventSystem.unsubscribe("stop_heartbeat", stopHeartbeat)
            break


def on_message(ws, message):
    json_message = json.loads(message)
    try:        
        op_code = json_message["op"] # ref: https://discord.com/developers/docs/topics/opcodes-and-status-codes#gateway-gateway-opcodes
        if op_code == 10:
            log.debug("Initialize heartbeat cycle...")
            heartbeatInterval = (json_message["d"]["heartbeat_interval"]/1000)-1
            log.info(f"Set heartbeat interval to {heartbeatInterval}s.")
            # Start heartbeat cycle
            newThread = threading.Thread(target=heartbeat, args=[ws, heartbeatInterval, True])
            newThread.daemon = True
            newThread.start()
            log.info("Start listening...")
        elif op_code == 6 or op_code == 7:
            reconnect_discord_ws()
        elif op_code == 0:
            sub = f"{Colorcode.gray}﹃{Colorcode.reset}"
            event = json_message["d"]
            intent = json_message["t"] # ref: https://discord.com/developers/docs/topics/gateway#gateway-intents
            messageID = event["id"] if "id" in event else None
            username = event["author"]["username"] if "author" in event else Colorcode.gray+"unknown"+Colorcode.reset
            userID = event["author"]["id"] if "author" in event else Colorcode.gray+"N/A"+Colorcode.reset
            serverID = event["guild_id"] if "guild_id" in event else None
            serverName = None
            if serverID != None:
                for server in define_server:
                    if serverID in server[0]:
                        serverName = server[1][0]
                        break

            channelID = event["channel_id"] if "channel_id" in event else None
            channelName = None
            for channel in define_channel:
                if channelID in channel[0]:
                    channelName = channel[1][0]
                    break
                if serverID is None:
                    channelName = "Direct Message"
                    break

            serverTag = f"[{serverName}({serverID})]" if serverName is not None and display_server_id is True and serverID != None else f"[{serverName}]" if serverName is not None and serverID != None else f"[{serverID}]" if display_server_id is True and serverID != None else ""
            channelTag = f"{channelName}({channelID})" if channelName is not None and display_channel_id is True else f"{channelName}" if channelName is not None else f"[{channelID}]" if display_channel_id is True else ""
            msgPrefix = f"{messageID} {serverTag}{' ➜  ' if serverTag != '' else ''}{channelTag} <{username}{f'({userID})' if display_user_id else ''}>: "

            if "content" in event and event["content"] != "":
                content = event["content"]
                multilineContent = ""
                if "\n" in content:
                    multilineContent = content.split("\n")
                    content = Colorcode.gray+"{This is a multiline content ⬇⬇⬇⬇ }"+Colorcode.reset
                msg = [f"{msgPrefix}{content}"]
                if multilineContent != "":
                    for ctx in multilineContent:
                        msg.append(f"{sub} {ctx}")

                def printOutput():
                    if "CREATE" in intent:
                        for ctx in msg:
                            log.msg(ctx)
                            storeMessages.append({'id': messageID, 'username': username,'content': content})
                    if "UPDATE" in intent:
                        result = next(
                        (item for item in storeMessages if item['id'] == messageID),
                        {}
                        )
                        for ctx in msg:
                            log.edit(ctx +" "+ "Before Edit: //"+ f"{result.get('content')}")
                            storeMessages.remove(result)
                            storeMessages.append({'id': messageID, 'username': username,'content': content})


                # filter
                if enable_server_whitelist and serverID in whitelist_sever:
                    if (enable_channel_whitelist and channelID in whitelist_channel) or (enable_channel_blacklist and channelID not in blacklist_channel) or (enable_channel_whitelist is False and enable_channel_blacklist is False):
                        printOutput()
                elif serverID is None and ((enable_channel_whitelist and channelID in whitelist_channel) or (enable_channel_blacklist and channelID not in blacklist_channel) or (enable_channel_whitelist is False and enable_channel_blacklist is False)):
                    printOutput()
                # log all messages
                elif enable_server_whitelist is False and enable_channel_whitelist is False and enable_server_blacklist is False and enable_channel_blacklist is False:
                    printOutput()
                
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

            # delete event
            if "DELETE" in intent:
                result = next(
                (item for item in storeMessages if item['id'] == messageID),
                {}
                )
                log.delete(f"{result.get('id')} "+f"<{result.get('username')}>: "+f"{result.get('content')}")
                storeMessages.remove(result)


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
    eventSystem.post_event("stop_heartbeat", True) # stop current heartbeat cycle
    connect_discord_ws()

if __name__ == "__main__":
    connect_discord_ws()
