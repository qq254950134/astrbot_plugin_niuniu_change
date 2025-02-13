from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
import json
import random
import time
import asyncio
from datetime import datetime
from pathlib import Path
import sqlite3
import os

class NiuUser:
    def __init__(self):
        self.user_id = ""  # 用户ID
        self.nickname = ""  # 昵称
        self.coins = 0  # 金币
        self.energy = 100  # 体力值
        self.last_sign = None  # 上次签到时间
        self.last_energy_time = None  # 上次体力恢复时间
        self.items = {}  # 道具背包
        self.level = 1  # 等级
        self.exp = 0  # 经验值
        self.no_color_days = 0  # 戒色天数
        self.last_color_time = None  # 上次打胶时间

class NiuGameDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 创建用户表
        c.execute('''CREATE TABLE IF NOT EXISTS users
                    (user_id TEXT PRIMARY KEY,
                     nickname TEXT,
                     coins INTEGER,
                     energy INTEGER,
                     last_sign TEXT,
                     last_energy_time TEXT,
                     items TEXT,
                     level INTEGER,
                     exp INTEGER,
                     no_color_days INTEGER,
                     last_color_time TEXT)''')
        conn.commit()
        conn.close()

    def save_user(self, user: NiuUser):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO users VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                 (user.user_id, user.nickname, user.coins, user.energy,
                  user.last_sign, user.last_energy_time, json.dumps(user.items),
                  user.level, user.exp, user.no_color_days, user.last_color_time))
        conn.commit()
        conn.close()

    def load_user(self, user_id: str) -> NiuUser:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
        data = c.fetchone()
        conn.close()
        
        if not data:
            return None
            
        user = NiuUser()
        user.user_id = data[0]
        user.nickname = data[1]
        user.coins = data[2]
        user.energy = data[3]
        user.last_sign = data[4]
        user.last_energy_time = data[5]
        user.items = json.loads(data[6])
        user.level = data[7]
        user.exp = data[8]
        user.no_color_days = data[9]
        user.last_color_time = data[10]
        return user

@register("niuhelper", "Your Name", "牛牛游戏插件", "1.0.0")
class NiuHelper(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        data_dir = Path("data/niuhelper")
        if not data_dir.exists():
            data_dir.mkdir(parents=True)
        self.db = NiuGameDB(str(data_dir / "niugame.db"))
        self.shop_items = {
            "体力药水": {"price": 100, "effect": "恢复50点体力"},
            "经验加倍卡": {"price": 200, "effect": "下次活动经验翻倍"},
            "戒色徽章": {"price": 500, "effect": "戒色成功率提升20%"}
        }
        # 启动体力恢复任务
        asyncio.create_task(self.energy_recovery_task())

    async def energy_recovery_task(self):
        """定时恢复用户体力的后台任务"""
        while True:
            await asyncio.sleep(300)  # 每5分钟执行一次
            # 这里可以添加体力恢复逻辑

    async def get_user(self, user_id: str, nickname: str = None) -> NiuUser:
        """获取用户数据,如果不存在则创建"""
        user = self.db.load_user(user_id)
        if not user:
            user = NiuUser()
            user.user_id = user_id
            user.nickname = nickname or user_id
            user.coins = 100  # 新用户赠送100金币
            self.db.save_user(user)
        return user

    @filter.command("注册牛牛")
    async def register(self, event: AstrMessageEvent, nickname: str = None):
        """注册牛牛账号"""
        user_id = event.get_sender_id()
        user = self.db.load_user(user_id)
        if user:
            yield event.plain_result("你已经注册过了哦!")
            return
            
        if not nickname:
            nickname = event.get_sender_name()
        user = await self.get_user(user_id, nickname)
        yield event.plain_result(f"注册成功! 赠送你100金币\n当前状态:\n昵称: {user.nickname}\n金币: {user.coins}\n体力: {user.energy}")

    @filter.command("签到")
    async def sign_in(self, event: AstrMessageEvent):
        """每日签到"""
        user = await self.get_user(event.get_sender_id())
        now = datetime.now()
        
        if user.last_sign and datetime.strptime(user.last_sign, "%Y-%m-%d").date() == now.date():
            yield event.plain_result("今天已经签到过了哦!")
            return
            
        coins = random.randint(50, 200)
        exp = random.randint(10, 30)
        user.coins += coins
        user.exp += exp
        user.last_sign = now.strftime("%Y-%m-%d")
        self.db.save_user(user)
        
        yield event.plain_result(f"签到成功!\n获得金币: {coins}\n获得经验: {exp}\n当前金币: {user.coins}")

    @filter.command("打胶")
    async def color(self, event: AstrMessageEvent):
        """打胶功能"""
        user = await self.get_user(event.get_sender_id())
        now = datetime.now()
        
        if user.energy < 20:
            yield event.plain_result("体力不足,无法打胶!")
            return
            
        if user.last_color_time:
            last_time = datetime.strptime(user.last_color_time, "%Y-%m-%d %H:%M:%S")
            if (now - last_time).seconds < 3600:
                yield event.plain_result("你刚打过,请休息一会儿!")
                return
        
        user.energy -= 20
        user.no_color_days = 0
        user.last_color_time = now.strftime("%Y-%m-%d %H:%M:%S")
        exp = random.randint(5, 15)
        user.exp += exp
        self.db.save_user(user)
        
        yield event.plain_result(f"打胶成功!\n消耗体力: 20\n获得经验: {exp}\n剩余体力: {user.energy}")

    @filter.command("比划比划")
    async def fight(self, event: AstrMessageEvent):
        """比划比划功能"""
        user = await self.get_user(event.get_sender_id())
        
        if user.energy < 30:
            yield event.plain_result("体力不足,无法比划!")
            return
        
        result = random.choice(["胜利", "失败"])
        coins = random.randint(50, 150)
        exp = random.randint(10, 30)
        
        if result == "胜利":
            user.coins += coins
            user.exp += exp
            message = f"比划胜利!\n获得金币: {coins}\n获得经验: {exp}"
        else:
            user.coins = max(0, user.coins - coins)
            message = f"比划失败!\n损失金币: {coins}"
            
        user.energy -= 30
        self.db.save_user(user)
        
        yield event.plain_result(f"{message}\n当前金币: {user.coins}\n剩余体力: {user.energy}")

    @filter.command("商店")
    async def shop(self, event: AstrMessageEvent):
        """显示商店"""
        shop_list = "商店物品列表:\n"
        for item, info in self.shop_items.items():
            shop_list += f"{item}: {info['price']}金币 - {info['effect']}\n"
        yield event.plain_result(shop_list)

    @filter.command("购买")
    async def buy(self, event: AstrMessageEvent, item_name: str):
        """购买物品"""
        if item_name not in self.shop_items:
            yield event.plain_result("没有这个物品!")
            return
            
        user = await self.get_user(event.get_sender_id())
        price = self.shop_items[item_name]["price"]
        
        if user.coins < price:
            yield event.plain_result("金币不足!")
            return
            
        user.coins -= price
        user.items[item_name] = user.items.get(item_name, 0) + 1
        self.db.save_user(user)
        
        yield event.plain_result(f"购买成功!\n物品: {item_name}\n花费: {price}金币\n剩余金币: {user.coins}")

    @filter.command("戒色")
    async def no_color(self, event: AstrMessageEvent):
        """查看戒色天数"""
        user = await self.get_user(event.get_sender_id())
        if not user.last_color_time:
            yield event.plain_result("你还从未打过胶,继续保持!")
            return
            
        last_time = datetime.strptime(user.last_color_time, "%Y-%m-%d %H:%M:%S")
        days = (datetime.now() - last_time).days
        
        if days > user.no_color_days:
            user.no_color_days = days
            self.db.save_user(user)
            
        yield event.plain_result(f"已经戒色 {days} 天了,继续加油!")

    @filter.command("状态")
    async def status(self, event: AstrMessageEvent):
        """查看状态"""
        user = await self.get_user(event.get_sender_id())
        status = f"用户状态:\n"
        status += f"昵称: {user.nickname}\n"
        status += f"等级: {user.level}\n"
        status += f"经验: {user.exp}\n"
        status += f"金币: {user.coins}\n"
        status += f"体力: {user.energy}\n"
        status += f"戒色天数: {user.no_color_days}\n"
        status += f"背包物品:\n"
        for item, count in user.items.items():
            status += f"- {item}: {count}个\n"
        yield event.plain_result(status)
