import random
import yaml
import os
import re
import time
from astrbot.api.all import *

# 定义 YAML 文件路径
PLUGIN_DIR = os.path.join('data', 'plugins', 'astrbot_plugin_niuniu')
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
        # 记录每个群中每个用户在 10 分钟内主动邀请的人数，格式为 {group_id: {user_id: (last_time, invited_count)}}
        self.invite_count = {}
        # 记录每个群中每个用户发起比划的冷却信息，格式为 {group_id: {user_id: {target_id: last_time}}}
        self.last_compare_time = {}

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

    @event_message_type(EventMessageType.ALL)
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

    @command("注册牛牛")
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

    @command("打胶")
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

            # 十分钟内不允许打胶
            MIN_COOLDOWN = 10 * 60
            if time_diff < MIN_COOLDOWN:
                cooldown_messages = [
                    f"{sender_nickname}，你的牛牛还在疲惫状态呢，至少再歇 10 分钟呀！",
                    f"{sender_nickname}，牛牛刚刚折腾完，还没缓过来，10 分钟内别再搞啦！",
                    f"{sender_nickname}，牛牛累得直喘气，10 分钟内可经不起再折腾咯！",
                    f"{sender_nickname}，牛牛正虚弱着呢，等 10 分钟让它恢复恢复吧！"
                ]
                yield event.plain_result(random.choice(cooldown_messages))
                return

            # 超过十分钟但低于三十分钟，越接近十分钟越容易失败
            THIRTY_MINUTES = 30 * 60
            if time_diff < THIRTY_MINUTES:
                failure_probability = (THIRTY_MINUTES - time_diff) / (THIRTY_MINUTES - MIN_COOLDOWN)
                config = self.get_niuniu_config()
                min_change = config.get('min_change', -5)
                max_change = config.get('max_change', 5)

                increase_messages = [
                    "{nickname}，你的牛牛还没完全恢复呢，但它潜力惊人，增长了{change}cm",
                    "{nickname}，你冒险打胶，没想到牛牛小宇宙爆发，增长了{change}cm",
                    "{nickname}，牛牛还软绵绵的，你却大胆尝试，结果增长了{change}cm"
                ]
                decrease_messages = [
                    "{nickname}，你的牛牛还没恢复，你就急于打胶，导致它缩短了{change}cm",
                    "{nickname}，你不顾牛牛疲惫，强行打胶，让它缩短了{change}cm",
                    "{nickname}，牛牛还在虚弱期，你却折腾它，缩短了{change}cm"
                ]
                no_effect_messages = [
                    "{nickname}，你的牛牛还没恢复，你打胶也没啥效果哦",
                    "{nickname}，牛牛没缓过来，你这次打胶白费劲啦",
                    "{nickname}，牛牛还没力气呢，打胶没作用"
                ]

                if self.check_probability(failure_probability):
                    change = random.randint(min_change, 0)
                    positive_change = -change
                    message = random.choice(decrease_messages).format(nickname=sender_nickname, change=positive_change)
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
                return

            # 三十分钟后正常判定
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
            # 更新上次打胶时间
            self.last_dajiao_time[user_id] = current_time
            yield event.plain_result(self.format_niuniu_message(message, user_info["length"]))
        else:
            yield event.plain_result(f"{sender_nickname}，你还没有注册牛牛，请先发送“注册牛牛”进行注册。")

    @command("我的牛牛")
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

    @command("比划比划")
    async def compare_niuniu(self, event: AstrMessageEvent, target_name: str = None):
        """比划比划指令处理函数"""
        user_id = str(event.get_sender_id())
        sender_nickname = event.get_sender_name()
        group_id = str(event.message_obj.group_id)

        if group_id and group_id in self.niuniu_lengths and user_id in self.niuniu_lengths[group_id]:
            at_users = self.parse_at_users(event)
            target_user_id = None

            if at_users:
                target_user_id = at_users[0]
            elif target_name:
                # 使用正则表达式进行模糊匹配
                pattern = re.compile(re.escape(target_name), re.IGNORECASE)
                matched_users = []
                for uid, info in self.niuniu_lengths[group_id].items():
                    if pattern.search(info["nickname"]):
                        matched_users.append(uid)
                if len(matched_users) == 0:
                    yield event.plain_result(f"{sender_nickname}，未找到包含 '{target_name}' 的已注册牛牛用户。")
                    return
                elif len(matched_users) > 1:
                    yield event.plain_result(f"{sender_nickname}，找到多个包含 '{target_name}' 的用户，请使用 @ 精确指定对手。")
                    return
                else:
                    target_user_id = matched_users[0]
            else:
                yield event.plain_result(f"{sender_nickname}，请 @ 一名已注册牛牛的用户或输入用户名关键词进行比划。")
                return

            if not target_user_id:
                yield event.plain_result(f"{sender_nickname}，请 @ 一名已注册牛牛的用户或输入用户名关键词进行比划。")
                return

            if target_user_id not in self.niuniu_lengths[group_id]:
                yield event.plain_result(f"{sender_nickname}，对方还没有注册牛牛呢！")
                return

            # 检查 10 分钟内邀请人数限制
            current_time = time.time()
            group_invite_count = self.invite_count.setdefault(group_id, {})
            last_time, count = group_invite_count.get(user_id, (0, 0))
            if current_time - last_time < 10 * 60:
                if count >= 3:
                    limit_messages = [
                        f"{sender_nickname}，你的牛牛刚比划了好几回，这会儿累得直喘气，得缓缓啦！",
                        f"{sender_nickname}，牛牛经过几次比划，已经累得软绵绵的，让它歇会儿吧！",
                        f"{sender_nickname}，你的牛牛连续比划，现在都有点颤颤巍巍了，快让它休息下！",
                        f"{sender_nickname}，牛牛比划了这么多次，已经疲惫不堪，没力气再比啦，先休息会儿！"
                    ]
                    yield event.plain_result(random.choice(limit_messages))
                    return
            else:
                count = 0
            group_invite_count[user_id] = (current_time, count + 1)

            # 检查冷却
            group_compare_time = self.last_compare_time.setdefault(group_id, {})
            user_compare_time = group_compare_time.setdefault(user_id, {})
            last_compare = user_compare_time.get(target_user_id, 0)
            MIN_COMPARE_COOLDOWN = 10 * 60  # 10 分钟冷却时间
            if current_time - last_compare < MIN_COMPARE_COOLDOWN:
                yield event.plain_result(f"{sender_nickname}，你在 10 分钟内已邀请过该用户比划，稍等一下吧。")
                return

            user_info = self.niuniu_lengths[group_id][user_id]
            target_info = self.niuniu_lengths[group_id][target_user_id]
            # 更新最后发起比划时间
            user_compare_time[target_user_id] = current_time

            user_length = user_info["length"]
            target_length = target_info["length"]
            diff = user_length - target_length

            # 增加随机事件：两败俱伤，长度减半
            double_loss_probability = 0.05  # 5% 的概率两败俱伤
            if self.check_probability(double_loss_probability):
                user_info["length"] = max(1, user_length // 2)
                target_info["length"] = max(1, target_length // 2)
                self._save_niuniu_lengths()
                # 以下两行缩进，属于 if 语句块
                yield event.plain_result(f"{sender_nickname} 和 {target_info['nickname']}，你们俩的牛牛刚一碰撞，就像两颗脆弱的玻璃珠，“啪嗒”一下都折断啦！双方的牛牛长度都减半咯！")
                return

            hardness_win_messages = [
                "{nickname}，虽然你们的牛牛长度相近，但你的牛牛如同钢铁般坚硬，一下子就碾压了对方，太厉害了！",
                "{nickname}，关键时刻，你的牛牛硬度爆棚，像一把利刃刺穿了对方的防线，成功战胜对手！",
                "{nickname}，长度差不多又怎样，你的牛牛凭借着惊人的硬度脱颖而出，霸气侧漏！"
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
                    yield event.plain_result(f"{sender_nickname} 和 {target_info['nickname']}，你们的牛牛长度差距不大，就像两位旗鼓相当的对手，继续加油哦！")
            elif diff > 0:
                config = self.get_niuniu_config()
                min_bonus = config.get('min_bonus', 0)
                max_bonus = config.get('max_bonus', 3)
                bonus = random.randint(min_bonus, max_bonus)
                user_info["length"] += bonus
                self._save_niuniu_lengths()
                win_messages = [
                    "{nickname}，你的牛牛就像一条威风凛凛的巨龙，以绝对的长度优势把 {target_nickname} 的牛牛打得节节败退，太威武啦！",
                    "{nickname}，你的牛牛如同一个勇猛的战士，用长长的身躯轻松碾压了 {target_nickname} 的牛牛，厉害极了！",
                    "{nickname}，你家牛牛简直就是王者降临，长度上把 {target_nickname} 远远甩在身后，让对方毫无还手之力！"
                ]
                message = random.choice(win_messages).format(nickname=sender_nickname, target_nickname=target_info["nickname"])
                yield event.plain_result(self.format_niuniu_message(
                    f"{message} 你的长度增加{bonus}cm",
                    user_info["length"]))
            else:
                config = self.get_niuniu_config()
                min_bonus = config.get('min_bonus', 0)
                max_bonus = config.get('max_bonus', 3)
                bonus = random.randint(min_bonus, max_bonus)
                target_info["length"] += bonus
                self._save_niuniu_lengths()
                lose_messages = [
                    "{nickname}，很可惜呀，这次你的牛牛就像一只小虾米，在长度上完全比不过 {target_nickname} 的大鲸鱼，下次加油呀！",
                    "{nickname}，{target_nickname} 的牛牛如同一个巨人，在长度上把你的牛牛秒成了渣渣，你别气馁，还有机会！",
                    "{nickname}，这一回你的牛牛就像一颗小豆芽，长度远远不及 {target_nickname} 的参天大树，再接再厉，争取下次赢回来！"
                ]
                message = random.choice(lose_messages).format(nickname=sender_nickname, target_nickname=target_info["nickname"])
                if bonus > 0:
                    target_new_length = target_info["length"]
                    if target_new_length >= 100:
                        length_str = f"{target_new_length / 100:.2f}m"
                    else:
                        length_str = f"{target_new_length}cm"
                    yield event.plain_result(f"{message} {target_info['nickname']} 的长度增加{bonus}cm，当前长度为{length_str}")
                else:
                    yield event.plain_result(f"{message} 不过 {target_info['nickname']} 的长度没有增加。")
        else:
            yield event.plain_result(f"{sender_nickname}，你还没有注册牛牛，请先发送“注册牛牛”进行注册。")

    @command("牛牛排行")
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

    @command("牛牛菜单")
    async def niuniu_menu(self, event: AstrMessageEvent):
        """牛牛菜单指令处理函数"""
        menu = """
牛牛游戏菜单：
1. 注册牛牛：开启你的牛牛之旅，随机获得初始长度的牛牛。
2. 打胶：通过此操作有机会让你的牛牛长度增加或减少，注意要等牛牛恢复好哦。
3. 我的牛牛：查看你当前牛牛的长度，并获得相应评价。
4. 比划比划：@ 一名已注册牛牛的用户，或输入用户名关键词，进行牛牛长度的较量。
5. 牛牛排行：查看当前群内牛牛长度的排行榜。
        """
        yield event.plain_result(menu)
