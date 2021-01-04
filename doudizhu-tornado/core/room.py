import logging

from core import Singleton
from core.table import Table

logger = logging.getLogger('ddz')

#有撮子还有房间
class Room(object):

    def __init__(self, uid , allow_robot=True):
        self.uid = uid
        # self.uidleft = luid
        # self.uidright = ruid
        self.__waiting_tables = {}
        self.__playing_tables = {}
        self.allow_robot = allow_robot
        self.entrance_fee = 100
        logger.info('ROOM[%d] CREATED创建房间 ', uid)

    def rsp_tables(self):
        rsp = []
        for _, t in self.waiting_tables.items():
            rsp.append([t.uid, t.size()])
        return rsp

    def new_table(self):
        t = Table(RoomManager.gen_table_id(), self)
        self.waiting_tables[t.uid] = t
        return t

    def find_waiting_table(self, uid):
        if uid == -1:
            for _, table in self.waiting_tables.items():
                return table
            return self.new_table()
        return self.waiting_tables.get(uid)

    def on_table_changed(self, table):
        # print("改变桌子房间状态 开始或者 等待")
        if table.is_full():
            self.waiting_tables.pop(table.uid, None)
            self.playing_tables[table.uid] = table
        if table.is_empty():
            self.playing_tables.pop(table.uid, None)
            self.waiting_tables[table.uid] = table

    @property
    def waiting_tables(self):
        return self.__waiting_tables

    @property
    def playing_tables(self):
        return self.__playing_tables


class RoomManager(object):
    __metaclass__ = Singleton
    #初始化直接就是 有机器人room 和无机器人room
    __room_dict = {
        1: Room(1, True),
        2: Room(2, False),
    }

    __current_table_id = 0

    @staticmethod
    def gen_table_id():
        RoomManager.__current_table_id += 1
        return RoomManager.__current_table_id

    @staticmethod
    def find_room(uid, created=False):
        room = RoomManager.__room_dict.get(uid)
        if not room and created:
            room = Room(uid)
            RoomManager.__room_dict[uid] = room
        return room
