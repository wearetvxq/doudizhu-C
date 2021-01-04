import functools
import json
import logging

from tornado.escape import json_decode
from tornado.websocket import WebSocketHandler, WebSocketClosedError

from config import RIGHT_ROBOT_UID
from core.player import Player
from core.robot import AiPlayer
from core.room import RoomManager, Room
from db import torndb
from .protocol import Protocol as Pt

logger = logging.getLogger('ddz')


def shot_turn(method):
    @functools.wraps(method)
    def wrapper(socket, packet):
        if socket.player.seat == socket.player.table.whose_turn:
            method(socket, packet)
        else:
            logger.warning('Player[%d] TURN CHEAT', socket.uid)
    return wrapper


class SocketHandler(WebSocketHandler):
    #反着来
    def __init__(self, application, request, **kwargs):
        print("init")
        super().__init__(application, request, **kwargs)
        self.db: torndb.Connection = self.application.db
        self.playerleft: Player = None
        self.playerright: Player = None
        self.online= 0
        self.robotuserRoom = RoomManager.find_room(1)
    #调试工具跨域了？
    def check_origin(self, origin):
        return True


    def data_received(self, chunk):
        logger.info('socket data_received')

    def get_current_user(self):
        logger.info('socket data_received1')
        return json_decode(self.get_secure_cookie("user"))

    @property
    def uid(self):
        if hasattr(self,"playerleft"):
            return self.playerleft.uid
        else:
            print("机器人客户端的消息")
            return  RIGHT_ROBOT_UID

    @property
    def room(self):
        return self.robotuserRoom

    # @authenticated
    def open(self):
        self.online+=1
        print(self.online)
        print(11111111)
        #每个web socket连接是是两个操作 use
        self.playerleft = Player(1, "1", self)
        self.playerleft = Player(1, "1", self)
        self.playerright = Player(2, "2", self)
        logger.info('SOCKET[%s] OPEN', self.playerleft.uid)
        self.playerrobot = None
        self.table=None
        self.playerleft.room = RoomManager.find_room(1)
        self.playerright.room = RoomManager.find_room(1)


    def on_close(self):
        # self.player.leave_table()
        logger.info('SOCKET[%s] CLOSE', )

    def on_message(self, message):
        # print(message)
        #机器人也是一个 独立的连接 他的消息过来了 怎么处理
        if type(message)==bytes:
            try:
                packet =json.loads(message.decode("utf-8"), strict=False)
                # print(packet)
            except Exception as e:
                packet =json.loads(message,strict=False)
                # print(packet)

        else:
            packet = json.loads(message)
        logger.info('REQ[%d]: %s', self.uid, packet)
        print("收到消息",packet)
        code = packet[0]
        if code == 0 :
            pass
        # if code == Pt.REQ_LOGIN:
        #     response = [Pt.RSP_LOGIN, self.player.uid, self.player.name]
        #     self.write_message(response)
        #
        # elif code == Pt.REQ_ROOM_LIST:
        #     self.write_message([Pt.RSP_ROOM_LIST])
        #
        # elif code == Pt.REQ_TABLE_LIST:
        #     self.write_message([Pt.RSP_TABLE_LIST, self.room.rsp_tables()])

        # elif code == Pt.REQ_JOIN_ROOM:
        #     #同时两个玩家进入
        #     logger.info("玩家进入 下一步  19 -1")
        #     self.player.room = RoomManager.find_room(1)
        #     logger.info("同时创建房间,并且运行机器人加入")
        #     self.write_message([Pt.RSP_JOIN_ROOM, self.room.rsp_tables()])
        # [21,[1,2,3,4,5,6,7,8,9,10,11,12,13]]
        elif code == Pt.REQ_NEW_TABLE:
            # TODO: check player was already in table.
            logger.info("创建桌子并加入 同时准备给牌")
            table = self.room.new_table()
            self.playerleft.join_table(table)
            print(table.players)

            self.playerright.join_table(table)
            print(table.players)

            #除了两个ai join
            #机器人也用此时的sefl socket就行ingress
            self.playerrobot = table.ai_join()
            self.playerrobot.socket=self

            self.playerrobot.join_table(table)
            self.table=table
            #这两个不是同一个table吗？ 机器人加入1号桌 报错没有 playerleft
            logger.info('PLAYER[%s] NEW TABLE[%d]', self.uid, table.uid)
            print("0到53的牌")
            print(table.players)
            if table.is_full():
                print("这里直接给机器人指定牌",packet[1])
                table.deal_poker(packet[1])
                self.room.on_table_changed(table)
                logger.info('TABLE[%s] GAME BEGIN[%s]', table.uid, table.players)
            # self.write_message([Pt.RSP_NEW_TABLE, table.uid])
        elif code == 2000:
            # TODO: check player was already in table.
            table=self.playerleft.table
            table.state=1
            #除了两个ai join
            #机器人也用此时的sefl socket就行ingress
            #这两个不是同一个table吗？ 机器人加入1号桌 报错没有 playerleft
            if table.is_full():
                print("这里直接给机器人指定牌",packet[1])
                table.deal_poker(packet[1])
                self.room.on_table_changed(table)
                logger.info('TABLE[%s] GAME BEGIN[%s]', table.uid, table.players)
            # self.write_message([Pt.RSP_NEW_TABLE, table.uid])

        elif code == Pt.REQ_JOIN_TABLE:
            #进入游戏 查找等待的桌子 并进去
            table = self.room.find_waiting_table(packet[1])# 找在等待的坐姿
            if not table:
                self.write_message([Pt.RSP_TABLE_LIST, self.room.rsp_tables()])
                logger.info('PLAYER[%d] JOIN TABLE[%d] NOT FOUND', self.uid, packet[1])
                return

            self.player.join_table(table)
            logger.info('PLAYER[%s] JOIN TABLE[%d]', self.uid, table.uid)
            if table.is_full():
                table.deal_poker()
                self.room.on_table_changed(table)
                logger.info('TABLE[%s] GAME BEGIN[%s]', table.uid, table.players)

#[33,0]
        elif code == Pt.REQ_CALL_SCORE:
            print("叫分？？？，这里应该是知道谁是地主 和由谁第一个出 ")
            self.handle_call_score(packet)

        elif code == Pt.REQ_DEAL_POKER:
            if self.player.table.state == 2:
                self.player.ready = True
            self.player.table.ready()


        #[37,0,]
        elif code == Pt.REQ_SHOT_POKER:
            print(packet)
            # print("出牌，机器人也是这个,看一下机器人出牌有没有影响",self.uid)
            if len(packet)==2:
                print("是收到的机器人出牌")
                self.handle_shot_poker(packet,RIGHT_ROBOT_UID)
            else:
                self.handle_shot_poker(packet,packet[1])
        elif code == Pt.REQ_CHAT:
            self.handle_chat(packet)
        elif code == Pt.REQ_CHEAT:
            self.handle_cheat(packet[1])
        elif code == Pt.REQ_Q_COMB:
            for p in self.player.table.players:
                if not isinstance(p, AiPlayer):
                    p.send([Pt.RSP_Q_COMB, packet[1:]])
        elif code == Pt.REQ_Q_FINE:
            for p in self.player.table.players:
                if not isinstance(p, AiPlayer):
                    p.send([Pt.RSP_Q_FINE, packet[1:]])
        elif code == Pt.REQ_RESTART:

            self.playerrobot.table.reset()
        else:
            logger.info('UNKNOWN PACKET: %s', code)

    # @shot_turn
    def handle_call_score(self, packet):
        seat = packet[1]
        dipai = packet[2]
        print("收到底牌和地主",dipai,seat)
        #直接传座位了 1 左边 2 右边 3 中间？  确认一下 出牌顺序
        self.playerrobot.handle_call_score(seat,dipai)

    # @shot_turn
    def handle_shot_poker(self, packet,seat):
        pokers = packet[1]
        print(seat)
        #机器人这个链接到底怎么处理的啊？？
        if seat==RIGHT_ROBOT_UID:
            print("机器人出牌")
            self.table= self.robotuserRoom.playing_tables[1] #todo 希望房间的id 是1
            # print(self.table,"暂时还好不用？？ 确实需要用啊 table 也没有")

            #此robot不是上面的# self.playerrobot.handle_shot_poker(pokers)
            # print(self.table.players,self.table.players[2].hand_pokers)
            self.table.whose_turn=2
            self.table.players[2].handle_shot_poker(pokers)
        elif seat==0:
            self.table.whose_turn=0
            print("0号位置出的牌为什么算到1号位置")
            pokers = packet[2]
            self.table.players[0].handle_shot_poker(pokers)
        elif seat==1:
            self.table.whose_turn=1
            pokers = packet[2]
            self.table.players[1].handle_shot_poker(pokers)
        else:
            print(seat,"座位号错了。。。。。。")
    def handle_chat(self, packet):
        if self.player.table:
            self.player.table.handle_chat(self.player, packet[1])

    def handle_cheat(self, uid):
        for p in self.player.table.players:
            if p.uid == uid:
                self.player.send([Pt.RSP_CHEAT, p.uid, p.hand_pokers])

    def write_message(self, message, binary=False):
        if self.ws_connection is None:
            raise WebSocketClosedError()
        logger.info('RSP[%d]: %s', self.uid, message)
        packet = json.dumps(message)
        return self.ws_connection.write_message(packet, binary=binary)

    def send_updates(cls, chat):
        logger.info('sending message to %d waiters', len(cls.waiters))
        for waiter in cls.waiters:
            waiter.write_message('tornado:' + chat)


