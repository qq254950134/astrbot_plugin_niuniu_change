import random
import yaml
import os
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import At
import time

# 定义 YAML 文件路径
PLUGIN_DIR = os.path.join('data', 'plugins', 'astrbot_plugin_niuniu-master')
if not os.path.exists(PLUGIN_DIR):
    os.makedirs(PLUGIN_DIR)
NIUNIU_LENGTHS_FILE = os.path.join(PLUGIN_DIR, 'niuniu_lengths.yml')


@register("niuniu_plugin", "长安某", "牛牛插件，包含注册牛牛、打胶、我的牛牛、比划比划、牛牛排行等功能", "1.0.0")
class NiuniuPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        if config is None:
            config = {}
        self.config = config
        self.niuniu_lengths = self._load_niuniu_lengths()
        # 记录每个用户的上次打胶时间
        self.last_dajiao_time = {}

    def _create_niuniu_lengths_file(self):
        """创建 niuniu_lengths.yml 文件"""
        if not os.path.exists(NIUNIU_LENGTHS_FILE):
            with open(NIUNIU_LENGTHS_FILE, 'w', encoding='utf-8') as file:
                yaml.dump({}, file, allow_unicode=True)

    def _load_niuniu_lengths(self):
        """从 YAML 文件中加载牛牛长度数据"""
        self._create_niuniu_lengths_file()
        try:
            with open(NIUNIU_LENGTHS_FILE, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file) or {}
        except FileNotFoundError:
            return {}
        except Exception:
            return {}

    def _save_niuniu_lengths(self):
        """将牛牛长度数据保存到 YAML 文件"""
        try:
            with open(NIUNIU_LENGTHS_FILE, 'w', encoding='utf-8') as file:
                yaml.dump(self.niuniu_lengths, file, allow_unicode=True)
        except Exception:
            pass

    def get_niuniu_config(self):
        """获取牛牛相关配置"""
        return self.config.get('niuniu_config', {})

    def check_probability(self, probability):
        """检查是否满足给定概率条件"""
        return random.random() < probability

    def format_niuniu_message(self, message, length):
        """格式化牛牛相关消息"""
        if length >= 100:
            length_str = f"{length / 100:.2f}m"
        else:
            length_str = f"{length}cm"
        return f"{message}，当前牛牛长度为{length_str}"

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def filter_messages(self, event: AstrMessageEvent):
        """全局事件过滤器，检查消息是否来自群聊"""
        group_id = event.message_obj.group_id if hasattr(event.message_obj, "group_id") else None
        if not group_id:
            return
        return event

    def parse_at_users(self, event: AstrMessageEvent):
        """解析消息中的 @ 用户"""
        chain = event.message_obj.message
        return [str(comp.qq) for comp in chain if isinstance(comp, At)]

    @filter.command("注册牛牛")
    async def register_niuniu(self, event: AstrMessageEvent):
        """注册牛牛指令处理函数"""
        user_id = str(event.get_sender_id())
        sender_nickname = event.get_sender_name()
        group_id = event.message_obj.group_id
        if group_id:
            if group_id not in self.niuniu_lengths:
                self.niuniu_lengths[group_id] = {}
            if user_id not in self.niuniu_lengths[group_id]:
                config = self.get_niuniu_config()
                min_length = config.get('min_length', 1)
                max_length = config.get('max_length', 10)
                length = random.randint(min_length, max_length)
                self.niuniu_lengths[group_id][user_id] = {
                    "nickname": sender_nickname,
                    "length": length
                }
                self._save_niuniu_lengths()
                yield event.plain_result(f"{sender_nickname}，注册成功，你的牛牛现在有{length} cm")
            else:
                yield event.plain_result(f"{sender_nickname}，你已经注册过牛牛啦！")
        else:
            yield event.plain_result("该指令仅限群聊中使用。")

    @filter.command("打胶")
    async def dajiao(self, event: AstrMessageEvent):
        """打胶指令处理函数"""
        user_id = str(event.get_sender_id())
        sender_nickname = event.get_sender_name()
        group_id = event.message_obj.group_id
        if group_id and group_id in self.niuniu_lengths and user_id in self.niuniu_lengths[group_id]:
            user_info = self.niuniu_lengths[group_id][user_id]
            # 检查冷却期
            current_time = time.time()
            last_time = self.last_dajiao_time.get(user_id, 0)
            time_diff = current_time - last_time

            # 定义冷却期范围（单位：秒）
            min_cooldown = 5 * 60  # 5 分钟
            max_cooldown = 2 * 60 * 60  # 2 小时
            base_cooldown = 30 * 60  # 30 分钟

            # 根据上次打胶时间动态调整冷却期
            if time_diff < min_cooldown:
                remaining_time = min_cooldown - time_diff
                yield event.plain_result(f"{sender_nickname}，你打胶太频繁啦，还需等待 {remaining_time:.0f} 秒（约 {remaining_time // 60} 分钟）才能再次打胶。")
                return

            # 随机生成冷却期，范围在 30 分钟到 2 小时之间
            cooldown = random.randint(base_cooldown, max_cooldown)

            if time_diff < cooldown:
                remaining_time = cooldown - time_diff
                yield event.plain_result(f"{sender_nickname}，你打胶太频繁啦，还需等待 {remaining_time:.0f} 秒（约 {remaining_time // 60} 分钟）才能再次打胶。")
                return

            # 根据时间间隔计算受伤概率
            # 时间间隔越短，受伤概率越大
            injury_probability = 1 - (time_diff / cooldown)
            config = self.get_niuniu_config()
            min_change = config.get('min_change', -5)
            max_change = config.get('max_change', 5)

            increase_messages = [
                "{nickname}，你嘿咻嘿咻一下，牛牛如同雨后春笋般茁壮成长，增长了{change}cm呢",
                "{nickname}，这一波操作猛如虎，牛牛蹭蹭地长了{change}cm，厉害啦！",
                "{nickname}，打胶效果显著，牛牛一下子就长了{change}cm，前途无量啊！"
            ]
            decrease_messages = [
                "{nickname}，哎呀，打胶过度，牛牛像被霜打的茄子，缩短了{-change}cm呢",
                "{nickname}，用力过猛，牛牛惨遭重创，缩短了{-change}cm，心疼它三秒钟",
                "{nickname}，这波操作不太妙，牛牛缩水了{-change}cm，下次悠着点啊！"
            ]
            no_effect_messages = [
                "{nickname}，这次打胶好像没什么效果哦，再接再厉吧",
                "{nickname}，打了个寂寞，牛牛没啥变化，再试试呗",
                "{nickname}，这波打胶无功而返，牛牛依旧岿然不动"
            ]

            if self.check_probability(injury_probability):
                # 受伤，缩短长度
                change = random.randint(min_change, -1)
                message = random.choice(decrease_messages).format(nickname=sender_nickname, change=change)
            else:
                change = random.randint(0, max_change)
                if change > 0:
                    message = random.choice(increase_messages).format(nickname=sender_nickname, change=change)
                else:
                    message = random.choice(no_effect_messages).format(nickname=sender_nickname)

            user_info["length"] += change
            if user_info["length"] < 1:
                user_info["length"] = 1
            self._save_niuniu_lengths()
            # 更新上次打胶时间
            self.last_dajiao_time[user_id] = current_time
            yield event.plain_result(self.format_niuniu_message(message, user_info["length"]))
        else:
            yield event.plain_result(f"{sender_nickname}，你还没有注册牛牛，请先发送“注册牛牛”进行注册。")

    @filter.command("我的牛牛")
    async def my_niuniu(self, event: AstrMessageEvent):
        """我的牛牛指令处理函数"""
        user_id = str(event.get_sender_id())
        sender_nickname = event.get_sender_name()
        group_id = event.message_obj.group_id
        if group_id and group_id in self.niuniu_lengths and user_id in self.niuniu_lengths[group_id]:
            user_info = self.niuniu_lengths[group_id][user_id]
            length = user_info["length"]

            # 根据长度给出评价
            if length <= 12:
                evaluations = ["像一只蚕宝宝", "小趴菜", "还处于萌芽阶段呢"]
            elif length <= 24:
                evaluations = ["表现还不错，继续加油", "中规中矩，有提升空间", "算是有点小实力啦"]
            elif length <= 36:
                evaluations = ["简直就是巨无霸", "太猛了，令人惊叹", "无敌的存在呀"]
            else:
                evaluations = ["突破天际的超级巨物", "神话般的存在，无人能及", "已经超越常理的长度啦"]

            evaluation = random.choice(evaluations)
            if length >= 100:
                length_str = f"{length / 100:.2f}m"
            else:
                length_str = f"{length}cm"
            yield event.plain_result(f"{sender_nickname}，你的牛牛长度为{length_str}，{evaluation}")
        else:
            yield event.plain_result(f"{sender_nickname}，你还没有注册牛牛，请先发送“注册牛牛”进行注册。")

    @filter.command("比划比划")
    async def compare_niuniu(self, event: AstrMessageEvent):
        """比划比划指令处理函数"""
        user_id = str(event.get_sender_id())
        sender_nickname = event.get_sender_name()
        group_id = event.message_obj.group_id
        if group_id and group_id in self.niuniu_lengths and user_id in self.niuniu_lengths[group_id]:
            at_users = self.parse_at_users(event)
            if at_users:
                target_user_id = at_users[0]
                if target_user_id in self.niuniu_lengths[group_id]:
                    user_info = self.niuniu_lengths[group_id][user_id]
                    target_info = self.niuniu_lengths[group_id][target_user_id]
                    user_length = user_info["length"]
                    target_length = target_info["length"]
                    diff = user_length - target_length

                    # 增加随机事件：两败俱伤，长度减半
                    double_loss_probability = 0.05  # 5% 的概率两败俱伤
                    if self.check_probability(double_loss_probability):
                        user_info["length"] = max(1, user_length // 2)
                        target_info["length"] = max(1, target_length // 2)
                        self._save_niuniu_lengths()
                        yield event.plain_result(f"{sender_nickname} 和 {target_info['nickname']}，发生了意外！双方的牛牛都折断了，长度都减半啦！")
                        return

                    hardness_win_messages = [
                        "{nickname}，虽然长度相近，但你凭借绝对的硬度碾压了对方，太厉害了！",
                        "{nickname}，关键时刻，你的牛牛硬度惊人，成功战胜对手！",
                        "{nickname}，长度差不多又如何，你以硬度取胜，霸气侧漏！"
                    ]

                    if abs(diff) <= 10:
                        if self.check_probability(0.3):
                            config = self.get_niuniu_config()
                            min_bonus = config.get('min_bonus', 0)
                            max_bonus = config.get('max_bonus', 3)
                            bonus = random.randint(min_bonus, max_bonus)
                            user_info["length"] += bonus
                            self._save_niuniu_lengths()
                            message = random.choice(hardness_win_messages).format(nickname=sender_nickname)
                            yield event.plain_result(self.format_niuniu_message(f"{message} 你的长度增加{bonus}cm",
                                                                                user_info["length"]))
                            return
                        else:
                            yield event.plain_result(f"{sender_nickname} 和 {target_info['nickname']}，你们的牛牛长度差距不大，继续加油哦！")
                    elif diff > 0:
                        config = self.get_niuniu_config()
                        min_bonus = config.get('min_bonus', 0)
                        max_bonus = config.get('max_bonus', 3)
                        bonus = random.randint(min_bonus, max_bonus)
                        user_info["length"] += bonus
                        self._save_niuniu_lengths()
                        yield event.plain_result(self.format_niuniu_message(
                            f"{sender_nickname}，你以绝对的长度令 {target_info['nickname']} 屈服了，你的长度增加{bonus}cm",
                            user_info["length"]))
                    else:
                        config = self.get_niuniu_config()
                        min_bonus = config.get('min_bonus', 0)
                        max_bonus = config.get('max_bonus', 3)
                        bonus = random.randint(min_bonus, max_bonus)
                        target_info["length"] += bonus
                        self._save_niuniu_lengths()
                        if bonus > 0:
                            target_new_length = target_info["length"]
                            if target_new_length >= 100:
                                length_str = f"{target_new_length / 100:.2f}m"
                            else:
                                length_str = f"{target_new_length}cm"
                            yield event.plain_result(f"{sender_nickname}，{target_info['nickname']} 以绝对的长度令你屈服了，对方长度增加{bonus}cm，当前长度为{length_str}")
                        else:
                            yield event.plain_result(f"{sender_nickname}，{target_info['nickname']} 以绝对的长度令你屈服了，但对方长度没有增加。")
                else:
                    yield event.plain_result(f"{sender_nickname}，对方还没有注册牛牛呢！")
            else:
                yield event.plain_result(f"{sender_nickname}，请 @ 一名已注册牛牛的用户进行比划。")
        else:
            yield event.plain_result(f"{sender_nickname}，你还没有注册牛牛，请先发送“注册牛牛”进行注册。")

    @filter.command("牛牛排行")
    async def niuniu_rank(self, event: AstrMessageEvent):
        """牛牛排行指令处理函数"""
        group_id = event.message_obj.group_id
        if group_id and group_id in self.niuniu_lengths:
            sorted_niuniu = sorted(self.niuniu_lengths[group_id].items(), key=lambda x: x[1]["length"], reverse=True)
            rank_message = "牛牛排行榜：\n"
            for i, (_, user_info) in enumerate(sorted_niuniu, start=1):
                nickname = user_info["nickname"]
                length = user_info["length"]
                if length >= 100:
                    length_str = f"{length / 100:.2f}m"
                else:
                    length_str = f"{length}cm"
                rank_message += f"{i}. {nickname}：{length_str}\n"
            yield event.plain_result(rank_message)
        else:
            yield event.plain_result("当前群里还没有人注册牛牛呢！")

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
