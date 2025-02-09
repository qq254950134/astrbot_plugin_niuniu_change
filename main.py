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
        # 记录每个用户的上次打胶时间和冷却时长
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
            last_time_info = self.last_dajiao_time.get(user_id, (0, 0))
            last_time = last_time_info[0]
            cooldown = last_time_info[1]
            time_diff = current_time - last_time

            # 30 分钟内不允许打胶
            MIN_COOLDOWN = 30 * 60
            if time_diff < MIN_COOLDOWN:
                cooldown_messages = [
                    f"{sender_nickname}，你打胶太频繁啦，悠着点呀！",
                    f"{sender_nickname}，别这么着急，打胶要适度哦！",
                    f"{sender_nickname}，打胶节奏太快啦，缓缓再搞！",
                    f"{sender_nickname}，这么频繁打胶可不行，歇会儿吧！"
                ]
                yield event.plain_result(random.choice(cooldown_messages))
                return

            # 随机生成冷却期，范围在 30 分钟到 2 小时之间
            if time_diff >= cooldown:
                cooldown = random.randint(MIN_COOLDOWN, 2 * 60 * 60)
            else:
                # 超过 30 分钟但没到冷却时长，计算失败概率
                failure_probability = (cooldown - time_diff) / (cooldown - MIN_COOLDOWN)

                config = self.get_niuniu_config()
                min_change = config.get('min_change', -5)
                max_change = config.get('max_change', 5)

                increase_messages = [
                    "{nickname}，你的牛牛还没恢复呢，但你强行打胶，没想到你的牛牛天赋惊人，增长了{change}cm",
                    "{nickname}，牛牛还在虚弱期，你强行打胶，结果牛牛超常发挥，增长了{change}cm",
                    "{nickname}，你的牛牛还没缓过来呢，不过你强行打胶，牛牛竟意外增长了{change}cm"
                ]
                decrease_messages = [
                    "{nickname}，你的牛牛还没好，你强行打胶，牛牛受伤了，缩短了{change}cm",
                    "{nickname}，牛牛还在恢复中，你强行打胶，导致牛牛长度减少了{change}cm",
                    "{nickname}，你的牛牛还很脆弱，你强行打胶，牛牛缩短了{change}cm"
                ]
                no_effect_messages = [
                    "{nickname}，你的牛牛还没恢复，你强行打胶，结果没啥效果",
                    "{nickname}，牛牛状态不佳，你强行打胶，这次打了个寂寞",
                    "{nickname}，你的牛牛还在虚弱，你强行打胶，牛牛没什么变化"
                ]

                if self.check_probability(failure_probability):
                    # 打胶失败，触发无变化效果
                    message = random.choice(no_effect_messages).format(nickname=sender_nickname)
                    change = 0
                else:
                    change = random.randint(min_change, max_change)
                    if change > 0:
                        message = random.choice(increase_messages).format(nickname=sender_nickname, change=change)
                    elif change < 0:
                        # 确保 change 是正数，用于格式化输出
                        positive_change = -change
                        message = random.choice(decrease_messages).format(nickname=sender_nickname, change=positive_change)
                    else:
                        message = random.choice(no_effect_messages).format(nickname=sender_nickname)

                user_info["length"] += change
                if user_info["length"] < 1:
                    user_info["length"] = 1
                self._save_niuniu_lengths()
                # 更新上次打胶时间和冷却时长
                self.last_dajiao_time[user_id] = (current_time, cooldown)
                yield event.plain_result(self.format_niuniu_message(message, user_info["length"]))
                return

            config = self.get_niuniu_config()
            min_change = config.get('min_change', -5)
            max_change = config.get('max_change', 5)

            increase_messages = [
                "{nickname}，你嘿咻嘿咻一下，牛牛如同雨后春笋般茁壮成长，增长了{change}cm呢",
                "{nickname}，这一波操作猛如虎，牛牛蹭蹭地长了{change}cm，厉害啦！",
                "{nickname}，打胶效果显著，牛牛一下子就长了{change}cm，前途无量啊！"
            ]
            decrease_messages = [
                "{nickname}，哎呀，打胶过度，牛牛像被霜打的茄子，缩短了{change}cm呢",
                "{nickname}，用力过猛，牛牛惨遭重创，缩短了{change}cm，心疼它三秒钟",
                "{nickname}，这波操作不太妙，牛牛缩水了{change}cm，下次悠着点啊！"
            ]
            no_effect_messages = [
                "{nickname}，这次打胶好像没什么效果哦，再接再厉吧",
                "{nickname}，打了个寂寞，牛牛没啥变化，再试试呗",
                "{nickname}，这波打胶无功而返，牛牛依旧岿然不动"
            ]

            change = random.randint(min_change, max_change)
            if change > 0:
                message = random.choice(increase_messages).format(nickname=sender_nickname, change=change)
            elif change < 0:
                positive_change = -change
                message = random.choice(decrease_messages).format(nickname=sender_nickname, change=positive_change)
            else:
                message = random.choice(no_effect_messages).format(nickname=sender_nickname)

            user_info["length"] += change
            if user_info["length"] < 1:
                user_info["length"] = 1
            self._save_niuniu_lengths()
            # 更新上次打胶时间和冷却时长
            self.last_dajiao_time[user_id] = (current_time, cooldown)
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
4. 比划比划：@ 一名已注册牛牛的用户，进行牛牛长度的较量。
5. 牛牛排行：查看当前群内牛牛长度的排行榜。
        """
        yield event.plain_result(menu)
