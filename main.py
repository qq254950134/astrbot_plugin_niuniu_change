import json
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import At, Plain

class NiuNiuData:
    def __init__(self):
        self.length: float = 0.0
        self.money: int = 0
        self.last_dajiao_time: datetime = None
        self.last_battle_time: datetime = None
        self.last_signin_time: datetime = None
        self.signin_days: int = 0
        self.is_jiesu: bool = False
        self.jiesu_start_time: datetime = None
        self.viagra_count: int = 0
        
class NiuNiuGame:
    def __init__(self):
        self.players: Dict[str, NiuNiuData] = {}
        self.load_data()
    
    def load_data(self):
        try:
            with open('niuniu_data.json', 'r') as f:
                data = json.load(f)
                for user_id, user_data in data.items():
                    player = NiuNiuData()
                    player.__dict__.update(user_data)
                    self.players[user_id] = player
        except FileNotFoundError:
            pass
    
    def save_data(self):
        data = {user_id: vars(player) for user_id, player in self.players.items()}
        with open('niuniu_data.json', 'w') as f:
            json.dump(data, f)

    def get_evaluation(self, length: float) -> str:
        if length <= 5:
            return "这也太短了，建议去医院看看🏥"
        elif length <= 10:
            return "勉强及格，继续努力💪"
        elif length <= 15:
            return "不错不错，有前途✨"
        elif length <= 20:
            return "牛牛界的新星⭐"
        else:
            return "卧槽！牛牛界的扛把子！👑"

@register("niuniu", "YourName", "牛牛养成游戏", "1.0.0")
class NiuNiuPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.game = NiuNiuGame()
        # 创建定时保存任务
        asyncio.create_task(self.auto_save())
        
    async def auto_save(self):
        while True:
            await asyncio.sleep(300)  # 每5分钟保存一次
            self.game.save_data()

    @filter.command("注册牛牛")
    async def register_niuniu(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        if user_id in self.game.players:
            yield event.plain_result("你已经有一头牛牛了，别贪心！🐮")
            return
        
        initial_length = round(random.uniform(5, 10), 1)
        player = NiuNiuData()
        player.length = initial_length
        player.money = 100  # 初始金币
        self.game.players[user_id] = player
        
        yield event.plain_result(f"🎉恭喜！你获得了一头{initial_length}cm的牛牛！\n"
                               f"评价：{self.game.get_evaluation(initial_length)}\n"
                               f"还赠送了100金币，快去商店看看吧！💰")

    @filter.command("打胶")
    async def dajiao(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        if user_id not in self.game.players:
            yield event.plain_result("你还没有牛牛，快去注册一个吧！📝")
            return
            
        player = self.game.players[user_id]
        
        # 检查冷却时间
        if (player.last_dajiao_time and 
            datetime.now() - datetime.fromisoformat(player.last_dajiao_time) < timedelta(minutes=30)):
            remaining = timedelta(minutes=30) - (datetime.now() - datetime.fromisoformat(player.last_dajiao_time))
            yield event.plain_result(f"你的牛牛还在不应期！需要休息{remaining.seconds//60}分钟！😮‍💨")
            return

        # 伟哥效果
        if player.viagra_count > 0:
            player.viagra_count -= 1
            result = random.uniform(0.5, 2.0)
            player.length += result
            yield event.plain_result(f"伟哥加持！牛牛增长了{result:.1f}cm！现在长度是{player.length:.1f}cm！🚀\n"
                                   f"剩余伟哥次数：{player.viagra_count}")
            return

        # 普通打胶
        result = random.choices(
            ['增长', '缩短', '无变化'],
            weights=[0.6, 0.2, 0.2]
        )[0]
        
        if result == '增长':
            gain = round(random.uniform(0.1, 1.0), 1)
            player.length += gain
            msg = f"嗨害嗨！牛牛增长了{gain}cm！现在长度是{player.length:.1f}cm！🎉"
        elif result == '缩短':
            loss = round(random.uniform(0.1, 0.5), 1)
            player.length = max(1, player.length - loss)
            msg = f"悲！打胶过猛，牛牛缩短了{loss}cm！现在长度是{player.length:.1f}cm！😱"
        else:
            msg = f"啥也没发生，牛牛抖了抖！现在长度还是{player.length:.1f}cm！😅"

        player.last_dajiao_time = datetime.now().isoformat()
        yield event.plain_result(msg + f"\n{self.game.get_evaluation(player.length)}")

    @filter.command("比划比划")
    async def battle(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        if user_id not in self.game.players:
            yield event.plain_result("你还没有牛牛，快去注册一个吧！📝")
            return
            
        # 获取被@的用户
        target_id = None
        for msg in event.message_obj.message:
            if isinstance(msg, At):
                target_id = msg.qq
                break
                
        if not target_id or target_id not in self.game.players:
            yield event.plain_result("你要跟谁比划？请@一个有牛牛的用户！👥")
            return
            
        if target_id == user_id:
            yield event.plain_result("不能和自己比划！你是要自己打自己吗？😅")
            return
            
        player = self.game.players[user_id]
        target = self.game.players[target_id]
        
        # 检查冷却时间
        if (player.last_battle_time and 
            datetime.now() - datetime.fromisoformat(player.last_battle_time) < timedelta(hours=1)):
            remaining = timedelta(hours=1) - (datetime.now() - datetime.fromisoformat(player.last_battle_time))
            yield event.plain_result(f"你的牛牛还在休息！需要{remaining.seconds//60}分钟才能再次比划！😮‍💨")
            return
            
        # 比划结果
        diff = abs(player.length - target.length)
        if player.length > target.length:
            result = f"胜利！你的牛牛比对方长{diff:.1f}cm！🏆"
            bonus = round(random.uniform(0.1, 0.5), 1)
            player.length += bonus
            result += f"\n获得额外成长{bonus}cm！"
        elif player.length < target.length:
            result = f"失败！你的牛牛比对方短{diff:.1f}cm！😢"
            penalty = round(random.uniform(0.1, 0.3), 1)
            player.length = max(1, player.length - penalty)
            result += f"\n萎缩了{penalty}cm..."
        else:
            result = "平局！你们的牛牛一样长！🤝"
            
        player.last_battle_time = datetime.now().isoformat()
        yield event.plain_result(f"比划结果：\n"
                               f"你的牛牛：{player.length:.1f}cm\n"
                               f"对方牛牛：{target.length:.1f}cm\n"
                               f"{result}")

    @filter.command("状态")
    async def status(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        if user_id not in self.game.players:
            yield event.plain_result("你还没有牛牛，快去注册一个吧！📝")
            return
            
        player = self.game.players[user_id]
        status = (f"🔍 你的牛牛状态：\n"
                 f"长度：{player.length:.1f}cm\n"
                 f"评价：{self.game.get_evaluation(player.length)}\n"
                 f"金币：{player.money}💰\n"
                 f"伟哥存量：{player.viagra_count}💊\n")
                 
        if player.is_jiesu:
            status += "当前状态：正在戒色中...😇"
            
        yield event.plain_result(status)

    @filter.command("排行榜")
    async def leaderboard(self, event: AstrMessageEvent):
        sorted_players = sorted(
            self.game.players.items(),
            key=lambda x: x[1].length,
            reverse=True
        )[:10]
        
        result = "🏆 牛牛长度排行榜 TOP10\n"
        for i, (user_id, player) in enumerate(sorted_players, 1):
            result += f"{i}. {user_id}: {player.length:.1f}cm {self.game.get_evaluation(player.length)}\n"
            
        yield event.plain_result(result)

    @filter.command("戒色")
    async def jiesu(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        if user_id not in self.game.players:
            yield event.plain_result("你还没有牛牛，快去注册一个吧！📝")
            return
            
        player = self.game.players[user_id]
        if player.is_jiesu:
            days = (datetime.now() - datetime.fromisoformat(player.jiesu_start_time)).days
            bonus = round(days * 0.5, 1)  # 每天奖励0.5cm
            player.length += bonus
            player.is_jiesu = False
            yield event.plain_result(f"功德圆满！戒色{days}天，牛牛增长了{bonus}cm！😇\n"
                                   f"现在长度是{player.length:.1f}cm")
        else:
            player.is_jiesu = True
            player.jiesu_start_time = datetime.now().isoformat()
            yield event.plain_result("你开始了戒色之旅！期待你的成长！🙏")

    @filter.command("商店")
    async def shop(self, event: AstrMessageEvent):
        shop_items = """💎 牛牛商店 💎
1. 伟哥 - 100金币/次
   - 效果：下次打胶必定增长0.5~2.0cm
2. 营养快线 - 50金币/次
   - 效果：立即增长0.5cm
        
使用方法：发送 购买 <物品编号> 即可"""
        yield event.plain_result(shop_items)

    @filter.command("购买")
    async def buy(self, event: AstrMessageEvent, item_id: int):
        user_id = event.get_sender_id()
        if user_id not in self.game.players:
            yield event.plain_result("你还没有牛牛，快去注册一个吧！📝")
            return
            
        player = self.game.players[user_id]
        
        if item_id == 1:  # 伟哥
            if player.money < 100:
                yield event.plain_result("你的金币不够！快去赚钱吧！💰")
                return
            player.money -= 100
            player.viagra_count += 1
            yield event.plain_result("购买成功！获得一次伟哥使用机会！💊")
        elif item_id == 2:  # 营养快线
            if player.money < 50:
                yield event.plain_result("你的金币不够！快去赚钱吧！💰")
                return
            player.money -= 50
            player.length += 0.5
            yield event.plain_result(f"购买成功！牛牛立即增长0.5cm！现在长度是{player.length:.1f}cm！🥛")
        else:
            yield event.plain_result("没有这个商品！请检查商品编号！❌")

    @filter.command("签到")
    async def signin(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        if user_id not in self.game.players:
            yield event.plain_result("你还没有牛牛，快去注册一个吧！📝")
            return
            
        player = self.game.players[user_id]
        
        # 检查是否已经签到
        today = datetime.now().date()
        if (player.last_signin_time and 
            datetime.fromisoformat(player.last_signin_time).date() == today):
            yield event.plain_result("你今天已经签到过了，明天再来吧！📅")
            return
            
        # 检查连续签到
        if (player.last_signin_time and 
            (today - datetime.fromisoformat(player.last_signin_time).date()).days == 1):
            player.signin_days += 1
        else:
            player.signin_days = 1
            
        # 签到奖励
        coins = random.randint(10, 50) + (player.signin_days * 5)  # 基础金币 + 连续签到奖励
        length_bonus = round(random.uniform(0.1, 0.3), 1)
        
        player.money += coins
        player.length += length_bonus
        player.last_signin_time = datetime.now().isoformat()
        
        yield event.plain_result(f"签到成功！🎉\n"
                               f"连续签到：{player.signin_days}天\n"
                               f"获得金币：{coins}💰\n"
                               f"牛牛增长：{length_bonus}cm\n"
                               f"当前长度：{player.length:.1f}cm")

    @filter.command("奇遇")
    async def adventure(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        if user_id not in self.game.players:
            yield event.plain_result("你还没有牛牛，快去注册一个吧！📝")
            return
            
        player = self.game.players[user_id]
        
        # 随机奇遇事件
        events = [
            {
                "name": "夜店艳遇",
                "desc": "在夜店邂逅绝色佳人，血脉喷张！",
                "effect": (3, 5),
                "type": "gain"
            },
            {
                "name": "仙人跳",
                "desc": "财色双失，牛牛遭重创！",
                "effect": (-5, -3),
                "type": "loss"
            },
            {
                "name": "修仙",
                "desc": "遇到修仙大佬，传授葵花宝典！",
                "effect": (2, 4),
                "type": "gain"
            },
            {
                "name": "踩到水坑",
                "desc": "不小心踩到冰冷的水坑，牛牛瑟瑟发抖！",
                "effect": (-2, -1),
                "type": "loss"
            },
            {
                "name": "晨跑",
                "desc": "清晨跑步遇到身材火辣的妹子，牛牛微微抬头！",
                "effect": (1, 2),
                "type": "gain"
            }
        ]
        
        # 80%概率触发事件，20%概率无事发生
        if random.random() < 0.8:
            event_data = random.choice(events)
            change = round(random.uniform(*event_data["effect"]), 1)
            
            if event_data["type"] == "gain":
                player.length += change
                yield event.plain_result(f"🎭 {event_data['name']}\n"
                                       f"{event_data['desc']}\n"
                                       f"牛牛增加了{change}cm！现在长度是{player.length:.1f}cm！")
            else:
                player.length = max(1, player.length + change)
                yield event.plain_result(f"😱 {event_data['name']}\n"
                                       f"{event_data['desc']}\n"
                                       f"牛牛缩短了{abs(change)}cm！现在长度是{player.length:.1f}cm！")
        else:
            yield event.plain_result("今天平平无奇，啥事也没发生~😴")

    @filter.command("帮助")
    async def help(self, event: AstrMessageEvent):
        help_text = """🎮 牛牛养成游戏指令列表 🎮

基础功能：
/注册牛牛 - 开始你的牛牛养成之旅
/打胶 - 尝试让牛牛变长
/比划比划 @某人 - 和别人比试比试
/状态 - 查看当前牛牛状态
/排行榜 - 查看牛牛排行榜

进阶功能：
/戒色 - 开始/结束戒色，获得额外奖励
/商店 - 查看商店物品
/购买 <物品编号> - 购买商店物品
/签到 - 每日签到领取奖励
/奇遇 - 触发随机奇遇事件

💡 小提示：
1. 打胶和比划都有冷却时间哦
2. 戒色越久奖励越多
3. 连续签到有额外奖励
4. 记得常来奇遇，好运气可能就降临了！"""
        yield event.plain_result(help_text)
