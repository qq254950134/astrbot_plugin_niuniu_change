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
        self.last_dajiao_time: str = None  # 存储ISO格式时间字符串
        self.last_battle_time: str = None
        self.last_signin_time: str = None
        self.signin_days: int = 0
        self.is_jiesu: bool = False
        self.jiesu_start_time: str = None
        self.viagra_count: int = 0
        self.titles: List[str] = []  # 称号列表
        self.current_title: str = None  # 当前佩戴的称号
        self.achievements: Dict[str, bool] = {  # 成就系统
            "初生牛犊": False,  # 注册成功
            "打胶之王": False,  # 累计打胶100次
            "牛魔王": False,    # 长度达到30cm
            "禁欲大师": False,  # 连续戒色7天
            "决斗王": False,    # 获得50次比划胜利
            "肝帝": False,      # 连续签到30天
        }
        self.stats = {  # 统计数据
            "total_dajiao": 0,  # 总打胶次数
            "battle_wins": 0,   # 比划胜利次数
            "max_length": 0.0,  # 历史最大长度
        }
        
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
            return "哈哈哈！这也叫牛牛？这明明是蚯蚓！🪱"
        elif length <= 10:
            return "这么短，你女朋友知道吗？建议赶紧去商店买点药！💊"
        elif length <= 15:
            return "一般般吧，至少能看得见了！👀"
        elif length <= 20:
            return "可以啊！羡慕死隔壁老王了！😎"
        elif length <= 25:
            return "卧槽！简直就是村东头扛把子！💪"
        elif length <= 30:
            return "恐怖如斯！这是要成精的节奏啊！🔥"
        else:
            return "这尼玛还是人吗？建议去国家地理杂志登记！📸"
            
    def get_title_bonus(self, title: str) -> dict:
        """获取称号加成"""
        title_effects = {
            "初生牛犊": {"dajiao_bonus": 0.1},  # 打胶收益+10%
            "打胶之王": {"dajiao_bonus": 0.2},  # 打胶收益+20%
            "牛魔王": {"battle_bonus": 0.2},   # 比划胜率+20%
            "禁欲大师": {"length_bonus": 0.1},  # 长度+10%
            "决斗王": {"battle_bonus": 0.3},   # 比划胜率+30%
            "肝帝": {"all_bonus": 0.1},       # 全属性+10%
        }
        return title_effects.get(title, {})

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
            yield event.plain_result("你还没有牛牛，快去注册一个吧！🎮")
            return
            
        player = self.game.players[user_id]
        
        # 计算称号加成
        title_bonus = ""
        if player.current_title:
            bonus = self.game.get_title_bonus(player.current_title)
            effects = []
            for k, v in bonus.items():
                if k == "dajiao_bonus":
                    effects.append(f"打胶收益+{int(v*100)}%")
                elif k == "battle_bonus":
                    effects.append(f"比划胜率+{int(v*100)}%")
                elif k == "length_bonus":
                    effects.append(f"长度+{int(v*100)}%")
                elif k == "all_bonus":
                    effects.append(f"全属性+{int(v*100)}%")
            if effects:
                title_bonus = f"称号加成：{', '.join(effects)}\n"
        
        status = (f"🔍 你的牛牛状态\n"
                 f"━━━━━━━━━━━━━━\n"
                 f"长度：{player.length:.1f}cm\n"
                 f"历史最长：{player.stats['max_length']:.1f}cm\n"
                 f"评价：{self.game.get_evaluation(player.length)}\n"
                 f"金币：{player.money}💰\n"
                 f"伟哥存量：{player.viagra_count}💊\n"
                 f"━━━━━━━━━━━━━━\n"
                 f"当前称号：{player.current_title or '无'}\n"
                 f"{title_bonus if title_bonus else ''}"
                 f"累计打胶：{player.stats['total_dajiao']}次\n"
                 f"比划战绩：{player.stats['battle_wins']}胜\n"
                 f"连续签到：{player.signin_days}天\n")
                 
        if player.is_jiesu:
            days = (datetime.now() - datetime.fromisoformat(player.jiesu_start_time)).days
            status += f"\n⛔️ 正在戒色中...\n已坚持{days}天，预计获得{days * 0.5:.1f}cm奖励！"
            
        yield event.plain_result(status)
        
    @filter.command("成就")
    async def achievements(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        if user_id not in self.game.players:
            yield event.plain_result("你还没有牛牛，快去注册一个吧！🎮")
            return
            
        player = self.game.players[user_id]
        
        achievement_desc = {
            "初生牛犊": {"desc": "注册成功", "reward": "打胶收益+10%"},
            "打胶之王": {"desc": "累计打胶100次", "reward": "打胶收益+20%"},
            "牛魔王": {"desc": "长度达到30cm", "reward": "比划胜率+20%"},
            "禁欲大师": {"desc": "连续戒色7天", "reward": "长度+10%"},
            "决斗王": {"desc": "获得50次比划胜利", "reward": "比划胜率+30%"},
            "肝帝": {"desc": "连续签到30天", "reward": "全属性+10%"}
        }
        
        result = "🏆 成就系统 🏆\n\n"
        for title, achieved in player.achievements.items():
            desc = achievement_desc[title]
            status = "✅" if achieved else "❌"
            result += f"{status} {title}\n"
            result += f"   条件：{desc['desc']}\n"
            result += f"   奖励：{desc['reward']}\n\n"
            
        result += "\n💡 提示：解锁成就后可获得对应称号加成！\n使用 /装备称号 <称号> 来装备解锁的称号"
        yield event.plain_result(result)

    @filter.command("装备称号")
    async def equip_title(self, event: AstrMessageEvent, title: str):
        user_id = event.get_sender_id()
        if user_id not in self.game.players:
            yield event.plain_result("你还没有牛牛，快去注册一个吧！🎮")
            return
            
        player = self.game.players[user_id]
        
        if not player.achievements.get(title, False):
            yield event.plain_result("你还没有解锁这个称号！继续努力吧！💪")
            return
            
        player.current_title = title
        yield event.plain_result(f"称号装备成功！\n当前称号：{title} 🏅")

    def check_achievements(self, player: NiuNiuData) -> List[str]:
        """检查并更新成就，返回新解锁的成就列表"""
        new_achievements = []
        
        # 检查各项成就条件
        if not player.achievements["初生牛犊"]:
            player.achievements["初生牛犊"] = True
            new_achievements.append("初生牛犊")
            
        if player.stats["total_dajiao"] >= 100 and not player.achievements["打胶之王"]:
            player.achievements["打胶之王"] = True
            new_achievements.append("打胶之王")
            
        if player.length >= 30 and not player.achievements["牛魔王"]:
            player.achievements["牛魔王"] = True
            new_achievements.append("牛魔王")
            
        if (player.is_jiesu and 
            (datetime.now() - datetime.fromisoformat(player.jiesu_start_time)).days >= 7 and 
            not player.achievements["禁欲大师"]):
            player.achievements["禁欲大师"] = True
            new_achievements.append("禁欲大师")
            
        if player.stats["battle_wins"] >= 50 and not player.achievements["决斗王"]:
            player.achievements["决斗王"] = True
            new_achievements.append("决斗王")
            
        if player.signin_days >= 30 and not player.achievements["肝帝"]:
            player.achievements["肝帝"] = True
            new_achievements.append("肝帝")
            
        return new_achievements

    def apply_title_effects(self, player: NiuNiuData, base_value: float, effect_type: str) -> float:
        """应用称号效果"""
        if not player.current_title:
            return base_value
            
        bonus = self.game.get_title_bonus(player.current_title)
        multiplier = 1.0
        
        if effect_type in bonus:
            multiplier += bonus[effect_type]
        if "all_bonus" in bonus:
            multiplier += bonus["all_bonus"]
            
        return base_value * multiplier

    @filter.command("购买")
    async def buy(self, event: AstrMessageEvent, item_id: int):
        user_id = event.get_sender_id()
        if user_id not in self.game.players:
            yield event.plain_result("你还没有牛牛，快去注册一个吧！🎮")
            return
            
        player = self.game.players[user_id]
        
        shop_items = {
            1: {"name": "伟哥", "price": 100, "effect": "viagra"},
            2: {"name": "营养快线", "price": 50, "effect": "instant_growth"},
            3: {"name": "肾宝片", "price": 200, "effect": "cooldown"},
            4: {"name": "古法秘籍", "price": 500, "effect": "permanent_bonus"},
            5: {"name": "护身符", "price": 300, "effect": "protection"},
            6: {"name": "幸运石", "price": 1000, "effect": "luck"},
            7: {"name": "双倍券", "price": 150, "effect": "double"},
            8: {"name": "延时喷剂", "price": 120, "effect": "delay"}
        }
        
        if item_id not in shop_items:
            yield event.plain_result("没有这个商品！请检查商品编号！❌")
            return
            
        item = shop_items[item_id]
        if player.money < item["price"]:
            yield event.plain_result(f"你的金币不够！还差{item['price'] - player.money}个金币！💰")
            return
            
        player.money -= item["price"]
        
        effect_msg = ""
        if item["effect"] == "viagra":
            player.viagra_count += 1
            effect_msg = "获得一次伟哥使用机会！下次打胶必定增长！💊"
        elif item["effect"] == "instant_growth":
            growth = 0.5
            player.length += growth
            effect_msg = f"牛牛立即增长{growth}cm！现在长度是{player.length:.1f}cm！🥛"
        # ... 其他道具效果处理 ...
        
        yield event.plain_result(f"购买成功！{effect_msg}")

    @filter.command("戒色")
    async def jiesu(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        if user_id not in self.game.players:
            yield event.plain_result("你还没有牛牛，快去注册一个吧！🎮")
            return
            
        player = self.game.players[user_id]
        
        if player.is_jiesu:
            days = (datetime.now() - datetime.fromisoformat(player.jiesu_start_time)).days
            
            if days < 1:
                yield event.plain_result("戒色不到一天就破戒了？太废物了！😒")
                return
                
            base_bonus = days * 0.5  # 基础奖励：每天0.5cm
            streak_bonus = 0.0  # 连续奖励
            
            if days >= 7:  # 7天以上给额外奖励
                streak_bonus = days * 0.1  # 每天额外0.1cm
                
            total_bonus = base_bonus + streak_bonus
            player.length += total_bonus
            player.is_jiesu = False
            
            # 检查是否达成戒色成就
            new_achievements = self.check_achievements(player)
            achievement_msg = ""
            if new_achievements:
                achievement_msg = f"\n\n🎉 解锁新成就：{', '.join(new_achievements)}"
            
            yield event.plain_result(
                f"艰难的戒色之旅结束了！\n"
                f"坚持天数：{days}天\n"
                f"基础奖励：{base_bonus:.1f}cm\n"
                f"额外奖励：{streak_bonus:.1f}cm\n"
                f"总共获得：{total_bonus:.1f}cm\n"
                f"现在长度：{player.length:.1f}cm"
                f"{achievement_msg}"
            )
        else:
            player.is_jiesu = True
            player.jiesu_start_time = datetime.now().isoformat()
            yield event.plain_result(
                "你开始了戒色之旅！\n"
                "提示：\n"
                "1. 每天可获得0.5cm基础奖励\n"
                "2. 坚持7天以上每天额外获得0.1cm\n"
                "3. 戒色期间禁止打胶\n"
                "4. 坚持越久奖励越多\n"
                "5. 戒色7天可获得成就【禁欲大师】\n\n"
                "加油！相信你可以的！🙏"
            )

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

    @filter.command("牛牛菜单")
    async def menu(self, event: AstrMessageEvent):
        menu_text = """🎮 牛牛养成游戏菜单 🎮

【基础系统】
/注册牛牛 - 获得你的专属牛牛，初始长度随机5-10cm
/打胶 - 30分钟一次，有机会增加牛牛长度
/比划比划 @某人 - 和别人比大小，赢了会获得额外成长！（1小时冷却）
/状态 - 查看你的牛牛状态、称号、成就等
/排行榜 - 看看谁是最强王者！

【进阶系统】
/戒色 - 暂时禁止打胶，但会积累能量，戒色结束时获得丰厚奖励
/奇遇 - 触发随机事件，欧皇请进！
/签到 - 每天签到领取奖励，连续签到有额外惊喜
/成就 - 查看可获得的称号和成就

【商店系统】
/商店 - 查看所有可购买的道具
/购买 <物品编号> - 购买商店里的道具

【小提示】
1. 打胶有一定概率变短，要谨慎！
2. 称号可以提供各种加成效果
3. 戒色越久，奖励越多，但要坚持住！
4. 商店里的道具可以让你变得更强
5. 打胶、比划、奇遇都可能触发成就

快来开始你的牛牛养成之旅吧！😎"""
        yield event.plain_result(menu_text)

    @filter.command("商店")
    async def shop(self, event: AstrMessageEvent):
        shop_items = """💎 牛牛商店 💎

【速效药品】
1. 伟哥 - 100金币/次
   - 效果：下次打胶必定增长0.5~2.0cm
2. 营养快线 - 50金币/次
   - 效果：立即增长0.5cm
3. 肾宝片 - 200金币/次
   - 效果：下次打胶冷却时间减半

【永久道具】
4. 古法秘籍 - 500金币
   - 效果：打胶基础收益永久提高20%
5. 护身符 - 300金币
   - 效果：防止打胶失败导致的长度减少
6. 幸运石 - 1000金币
   - 效果：奇遇触发概率提高50%

【限时道具】
7. 双倍券 - 150金币
   - 效果：2小时内所有收益翻倍
8. 延时喷剂 - 120金币
   - 效果：下3次打胶必定不会缩短

使用方法：发送 购买 <物品编号> 即可
温馨提示：道具可以叠加使用，效果更好哦！😉"""
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
