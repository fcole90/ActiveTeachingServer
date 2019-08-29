import websocket

from bot_client.basic import MySocket
from bot_client.act_r import ActRSocket

websocket.enableTrace(True)


def run_random():

    ws = MySocket(register_replies=False)
    ws.run_forever()


def run_act_r():

    ws = ActRSocket(waiting_time=0,
                    n_iteration=1000,
                    param={"d": 0.5, "tau": 0.01, "s": 0.06})
    ws.run_forever()


def main():

    run_random()


if __name__ == "__main__":

    main()
