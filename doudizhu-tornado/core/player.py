import logging
from typing import List

from tornado.websocket import WebSocketHandler

from core import rule
from handlers.protocol import Protocol as Pt

logger = logging.getLogger('ddz')

FARMER = 1
LANDLORD = 2


class Player(object):
    def __init__(self, uid: int, name: str, socket: WebSocketHandler = None):
        from core.table import Table
        self.uid = uid
        self.name = name
        self.socket = socket
        self.room = None
        self.table: Table = []
        self.ready = False
        self.seat = 0
        self.is_called = False
        self.role = FARMER
        self.hand_pokers: List[int] = []
        self.become_controller = False

    def reset(self):
        self.ready = False
        self.is_called = False
        self.role = FARMER
        self.hand_pokers: List[int] = []

    def send(self, packet):
        self.socket.write_message(packet)

    def handle_call_score(self, seat,dipai):
        # if 0 < score < self.table.call_score:
        #     logger.warning('Player[%d] CALL SCORE[%d] CHEAT', self.uid, score)
        #     return
        #
        # if score > 3:
        #     logger.warning('Player[%d] CALL SCORE[%d] CHEAT', self.uid, score)
        #     return

        self.is_called = True

        # next_seat = (self.seat + 1) % 3
        call_end=True
        # call_end = score == 3 or self.table.all_called()
        # if not call_end:
        #     self.table.whose_turn = next_seat
        # if score > 0:
        self.table.last_shot_seat = seat
        # if score > self.table.max_call_score:
        self.table.max_call_score = 3
        self.table.max_call_score_turn = seat
        self.whose_turn=seat
        self.table.pokers = dipai
        response = [Pt.RSP_CALL_SCORE, self.uid, 3, 3]
        for p in self.table.players:
            p.send(response)

        if call_end:
            self.table.call_score_end()

    def handle_shot_poker(self, pokers):
        # print(pokers)
        self.become_controller = False
        # print(self.table.uid,"确认一下至少websocket 和机器人里面的是同一个table")
        # print(self.table.whose_turn)
        self.table.out_cards[self.table.whose_turn] = pokers
        self.table.log.append((self.uid, pokers))
        if pokers:
            # print("牌型检测无所谓")
            # print(self.hand_pokers,"这里两个其他人需要处理一下")
            # print(self.seat)
            if self.seat!=2:
                for k,v in enumerate(pokers):
                    self.hand_pokers[k]=v
            # print(self.hand_pokers,"这里两个其他人需要处理一下")

            if not rule.is_contains(self.hand_pokers, pokers):
                logger.warning('Player[%d] play non-exist poker', self.uid)
                return

            if self.table.last_shot_seat != self.seat and rule.compare_poker(pokers, self.table.last_shot_poker) < 0:
                logger.warning('Player[%d] play small than last shot poker', self.uid)
                return
        else:
            print(self.uid,pokers,"不要就是传空")
        if pokers:
            self.become_controller = True
            self.table.history[self.seat] += pokers
            self.table.last_shot_seat = self.seat
            self.table.last_shot_poker = pokers
            for p in pokers:
                self.hand_pokers.remove(p)

        if self.hand_pokers:
            self.table.go_next_turn()

        import debug
        if self.uid == debug.over_in_advance:
            print("这里结束的？？地主的牌没有给到位！！！")
        #     self.table.on_game_over(self)
        #     return
        #
        if not self.hand_pokers:
            print("游戏结束不是我说的算！！！")
            self.table.game_over = True
            self.table.on_game_over(self)

        response = [Pt.RSP_SHOT_POKER, self.uid, pokers]
        for p in self.table.players:
            p.send(response)
        logger.info('Player[%d] shot[%s]', self.uid, str(pokers))
        # print("打印一下桌子的信息确认一下")
        print("下一个出牌",self.table.whose_turn)
        # print(self.table.last_shot_seat)
        # print(self.table.out_cards)
        # print(self.table.last_shot_poker)
        print(self.table.history)
        # print(self.table.state)
        if self.table.whose_turn==2 and self.table.state==1:
            print("到机器人自动出牌了")
            self.table.players[2].auto_shot_poker()

    def join_table(self, t):
        self.ready = True
        self.table = t
        t.on_join(self)

    def leave_table(self):
        self.ready = False
        if self.table:
            self.table.on_leave(self)
        # self.table = None

    def __repr(self):
        return self.__str__()

    def __str__(self):
        return str(self.uid) + '-' + self.name
