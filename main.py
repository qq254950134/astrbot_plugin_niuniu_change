import random
import yaml
import os
import logging
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import At
import time

# 定义 YAML 文件路径
NIUNIU_LENGTHS_FILE = 'niuniu_lengths.yml'

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@register("niuniu_plugin", "长安某", "牛牛插件，包含注册牛牛、打胶、我的牛牛、比划比划、牛牛排行等功能", "1.0.0")
class NiuniuPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.niuniu_lengths = self._load_niuniu_lengths()
        self.last_dajiao_time = {}
        logger.info(f"插件配置: {self.config}")

    def _manage_file(self, mode='r'):
        """管理文件的读取和写入操作"""
        try:
            if mode == 'w':
                if not os.path.exists(NIUNIU_LENGTHS_FILE):
                    with open(NIUNIU_LENGTHS_FILE, 'w', encoding='utf-8') as file:
                        yaml.dump({}, file, allow_unicode=True)
                    logger.info(f"成功创建 {NIUNIU_LENGTHS_FILE} 文件")
            with open(NIUNIU_LENGTHS_FILE, mode, encoding='utf-8') as file:
                if mode == 'r':
                    data = yaml.safe_load(file)
                    return data if data else {}
                elif mode == 'w':
                    yaml.dump(self.niuniu_lengths, file, allow_unicode=True)
                    logger.info(f"成功保存数据到 {NIUNIU_LENGTHS_FILE} 文件")
        except FileNotFoundError:
            if mode == 'r':
                # 尝试创建文件
                try:
                    with open(NIUNIU_LENGTHS_FILE, 'w', encoding='utf-8') as file:
                        yaml.dump({}, file, allow_unicode=True)
                    logger.info(f"在读取时发现文件不存在，成功创建 {NIUNIU_LENGTHS_FILE} 文件")
                    with open(NIUNIU_LENGTHS_FILE, 'r', encoding='utf-8') as file:
                        data = yaml.safe_load(file)
                        return data if data else {}
                except Exception as e:
                    logger.error(f"在读取时尝试创建 {NIUNIU_LENGTHS_FILE} 文件出错: {e}", exc_info=True)
                    return {}
        except Exception as e:
            logger.error(f"文件操作 {mode} 时出错: {e}", exc_info=True)
            return {} if mode == 'r' else None

    def _load_niuniu_lengths(self):
        """从 YAML 文件中加载牛牛长度数据"""
        return self._manage_file('r')

    def _save_niuniu_lengths(self):
        """将牛牛长度数据保存到 YAML 文件"""
        self._manage_file('w')

    def get_niuniu_config(self):
        """获取牛牛相关配置"""
        return self.config.get('niuniu_config', {})

    def check_probability(self, probability):
        """检查是否满足给定概率条件"""
        return random.random() < probability

    def format_niuniu_message(self, message, length):
        """格式化牛牛相关消息"""
        length_str = f"{length / 100:.2f}m" if length >= 100 else f"{length}cm"
        return f"{message}，当前牛牛长度为{length_str}"

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def filter_messages(self, event: AstrMessageEvent):
        """全局事件过滤器，检查消息是否来自群聊"""
        group_id = getattr(event.message_obj, "group_id", None)
        if not group_id:
            logger.info("消息不是来自群聊，忽略处理")
            return
        return event

    def parse_at_users(self, event: AstrMessageEvent):
        """解析消息中的 @ 用户"""
        return [str(comp.qq) for comp in event.message_obj.message if isinstance(comp, At)]

    async def get_nickname(self, group_id, user_id):
        """获取用户昵称"""
        bot = self.context.get_bot()
        try:
            member_info = await bot.get_group_member_info(group_id=int(group_id), user_id=int(user_id))
            return member_info.get("nickname", "未知用户")
        except Exception as e:
            logger.warning(f"获取用户 {user_id} 昵称时出错: {e}", exc_info=True)
            return "未知用户"

    @filter.command("注册牛牛")
    async def register_niuniu(self, event: AstrMessageEvent):
        """注册牛牛指令处理函数"""
        user_id = str(event.get_sender_id())
        group_id = event.message_obj.group_id
        if not group_id:
            yield event.plain_result("该指令仅限群聊中使用。")
            return
        group_data = self.niuniu_lengths.setdefault(group_id, {})
        if user_id in group_data:
            yield event.plain_result("你已经注册过牛牛啦！")
            return
        config = self.get_niuniu_config()
        length = random.randint(config.get('min_length', 1), config.get('max_length', 10))
        nickname = await self.get_nickname(group_id, user_id)
        group_data[user_id] = {"length": length, "nickname": nickname}
        self._save_niuniu_lengths()
        yield event.plain_result(f"注册成功，你的牛牛现在有{length} cm")

    @filter.command("打胶")
    async def dajiao(self, event: AstrMessageEvent):
        """打胶指令处理函数"""
        user_id = str(event.get_sender_id())
        group_id = event.message_obj.group_id
        if not (group_id and group_id in self.niuniu_lengths and user_id in self.niuniu_lengths[group_id]):
            yield event.plain_result("你还没有注册牛牛，请先发送“注册牛牛”进行注册。")
            return
        current_time = time.time()
        last_time = self.last_dajiao_time.get(user_id, 0)
        time_diff = current_time - last_time
        min_cooldown = 5 * 60
        max_cooldown = 2 * 60 * 60
        base_cooldown = 30 * 60
        if time_diff < min_cooldown:
            remaining_time = min_cooldown - time_diff
            yield event.plain_result(f"你打胶太频繁啦，还需等待 {remaining_time:.0f} 秒（约 {remaining_time // 60} 分钟）才能再次打胶。")
            return
        cooldown = random.randint(base_cooldown, max_cooldown)
        if time_diff < cooldown:
            remaining_time = cooldown - time_diff
            yield event.plain_result(f"你打胶太频繁啦，还需等待 {remaining_time:.0f} 秒（约 {remaining_time // 60} 分钟）才能再次打胶。")
            return
        injury_probability = 1 - (time_diff / cooldown)
        config = self.get_niuniu_config()
        min_change = config.get('min_change', -5)
        max_change = config.get('max_change', 5)
        messages = {
            'increase': [
                "你嘿咻嘿咻一下，牛牛如同雨后春笋般茁壮成长，增长了{change}cm呢",
                "这一波操作猛如虎，牛牛蹭蹭地长了{change}cm，厉害啦！",
                "打胶效果显著，牛牛一下子就长了{change}cm，前途无量啊！"
            ],
            'decrease': [
                "哎呀，打胶过度，牛牛像被霜打的茄子，缩短了{-change}cm呢",
                "用力过猛，牛牛惨遭重创，缩短了{-change}cm，心疼它三秒钟",
                "这波操作不太妙，牛牛缩水了{-change}cm，下次悠着点啊！"
            ],
            'no_effect': [
                "这次打胶好像没什么效果哦，再接再厉吧",
                "打了个寂寞，牛牛没啥变化，再试试呗",
                "这波打胶无功而返，牛牛依旧岿然不动"
            ]
        }
        if self.check_probability(injury_probability):
            change = random.randint(min_change, -1)
            message = random.choice(messages['decrease']).format(change=change)
        else:
            change = random.randint(0, max_change)
            message = random.choice(messages['increase' if change > 0 else 'no_effect']).format(change=change)
        user_info = self.niuniu_lengths[group_id][user_id]
        user_info["length"] = max(1, user_info["length"] + change)
        self._save_niuniu_lengths()
        self.last_dajiao_time[user_id] = current_time
        yield event.plain_result(self.format_niuniu_message(message, user_info["length"]))

    @filter.command("我的牛牛")
    async def my_niuniu(self, event: AstrMessageEvent):
        """我的牛牛指令处理函数"""
        user_id = str(event.get_sender_id())
        group_id = event.message_obj.group_id
        if not (group_id and group_id in self.niuniu_lengths and user_id in self.niuniu_lengths[group_id]):
            yield event.plain_result("你还没有注册牛牛，请先发送“注册牛牛”进行注册。")
            return
        length = self.niuniu_lengths[group_id][user_id]["length"]
        evaluations = {
            (0, 12): ["像一只蚕宝宝", "小趴菜", "还处于萌芽阶段呢"],
            (13, 24): ["表现还不错，继续加油", "中规中矩，有提升空间", "算是有点小实力啦"],
            (25, 36): ["简直就是巨无霸", "太猛了，令人惊叹", "无敌的存在呀"],
            (37, float('inf')): ["突破天际的超级巨物", "神话般的存在，无人能及", "已经超越常理的长度啦"]
        }
        for range_, eval_list in evaluations.items():
            if range_[0] <= length <= range_[1]:
                evaluation = random.choice(eval_list)
                break
        length_str = f"{length / 100:.2f}m" if length >= 100 else f"{length}cm"
        yield event.plain_result(f"你的牛牛长度为{length_str}，{evaluation}")

    @filter.command("比划比划")
    async def compare_niuniu(self, event: AstrMessageEvent):
        """比划比划指令处理函数"""
        user_id = str(event.get_sender_id())
        group_id = event.message_obj.group_id
        if not (group_id and group_id in self.niuniu_lengths and user_id in self.niuniu_lengths[group_id]):
            yield event.plain_result("你还没有注册牛牛，请先发送“注册牛牛”进行注册。")
            return
        at_users = self.parse_at_users(event)
        if not at_users:
            yield event.plain_result("请 @ 一名已注册牛牛的用户进行比划。")
            return
        target_user_id = at_users[0]
        if target_user_id not in self.niuniu_lengths[group_id]:
            yield event.plain_result("对方还没有注册牛牛呢！")
            return
        user_length = self.niuniu_lengths[group_id][user_id]["length"]
        target_length = self.niuniu_lengths[group_id][target_user_id]["length"]
        diff = user_length - target_length
        double_loss_probability = 0.05
        if self.check_probability(double_loss_probability):
            self.niuniu_lengths[group_id][user_id]["length"] = max(1, user_length // 2)
            self.niuniu_lengths[group_id][target_user_id]["length"] = max(1, target_length // 2)
            self._save_niuniu_lengths()
            yield event.plain_result("发生了意外！双方的牛牛都折断了，长度都减半啦！")
            return
        hardness_win_messages = [
            "虽然长度相近，但你凭借绝对的硬度碾压了对方，太厉害了！",
            "关键时刻，你的牛牛硬度惊人，成功战胜对手！",
            "长度差不多又如何，你以硬度取胜，霸气侧漏！"
        ]
        config = self.get_niuniu_config()
        min_bonus = config.get('min_bonus', 0)
        max_bonus = config.get('max_bonus', 3)
        if abs(diff) <= 10:
            if self.check_probability(0.3):
                bonus = random.randint(min_bonus, max_bonus)
                self.niuniu_lengths[group_id][user_id]["length"] += bonus
                self._save_niuniu_lengths()
                message = random.choice(hardness_win_messages)
                yield event.plain_result(self.format_niuniu_message(f"{message} 你的长度增加{bonus}cm",
                                                                    self.niuniu_lengths[group_id][user_id]["length"]))
            else:
                yield event.plain_result("你们的牛牛长度差距不大，继续加油哦！")
        elif diff > 0:
            bonus = random.randint(min_bonus, max_bonus)
            self.niuniu_lengths[group_id][user_id]["length"] += bonus
            self._save_niuniu_lengths()
            yield event.plain_result(self.format_niuniu_message(
                f"你以绝对的长度令对方屈服了，你的长度增加{bonus}cm",
                self.niuniu_lengths[group_id][user_id]["length"]))
        else:
            bonus = random.randint(min_bonus, max_bonus)
            self.niuniu_lengths[group_id][target_user_id]["length"] += bonus
            self._save_niuniu_lengths()
            if bonus > 0:
                target_new_length = target_length + bonus
                length_str = f"{target_new_length / 100:.2f}m" if target_new_length >= 100 else f"{target_new_length}cm"
                yield event.plain_result(f"对方以绝对的长度令你屈服了，对方长度增加{bonus}cm，当前长度为{length_str}")
            else:
                yield event.plain_result("对方以绝对的长度令你屈服了，但长度没有增加。")

    @filter.command("牛牛排行")
    async def niuniu_rank(self, event: AstrMessageEvent):
        """牛牛排行指令处理函数"""
        group_id = event.message_obj.group_id
        if not (group_id and group_id in self.niuniu_lengths):
            yield event.plain_result("当前群里还没有人注册牛牛呢！")
            return
        sorted_niuniu = sorted(self.niuniu_lengths[group_id].items(), key=lambda x: x[1]["length"], reverse=True)
        rank_message = "牛牛排行榜：\n"
        for i, (_, info) in enumerate(sorted_niuniu, start=1):
            length = info["length"]
            nickname = info["nickname"]
            length_str = f"{length / 100:.2f}m" if length >= 100 else f"{length}cm"
            rank_message += f"{i}. {nickname}：{length_str}\n"
        yield event.plain_result(rank_message)

    @filter.command("牛牛菜单")
    async def niuniu_menu(self, event: AstrMessageEvent):
        """牛牛菜单指令处理函数"""
        menu = """
牛牛游戏菜单：
1. 注册牛牛：开启你的牛牛之旅，随机获得初始长度的牛牛。
2. 打胶：通过此操作有机会让你的牛牛长度增加或减少，注意有冷却时间哦。
3. 我的牛牛：查看你当前牛牛的长度，并获得相应评价。
4. 比划比划：@ 一名已注册牛牛的用户，与对方比较牛牛长度，获胜方有机会增加长度。
5. 牛牛排行：查看当前群内牛牛长度的排行榜。
        """
        yield event.plain_result(menu)
