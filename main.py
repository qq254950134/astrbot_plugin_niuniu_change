import random
import yaml
import os
import json
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import At
from typing import List
from astrbot.api.message_components import BaseMessageComponent
from astrbot.api.message import MessageType, MessageMember

# 定义 YAML 文件路径
NIUNIU_LENGTHS_FILE = 'niuniu_lengths.yml'

# 注册插件
@register("niuniu_plugin", "作者名", "牛牛插件，包含注册牛牛、打胶、我的牛牛、比划比划、牛牛排行等功能", "1.0.0")
class NiuniuPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        # 接收配置字典
        self.config = config
        # 自动创建 niuniu_lengths.yml 文件
        self.create_niuniu_lengths_file()
        # 从 YAML 文件中加载牛牛长度数据
        self.niuniu_lengths = self.load_niuniu_lengths()
        print(f"插件配置: {self.config}")

    def create_niuniu_lengths_file(self):
        # 创建 niuniu_lengths.yml 文件
        if not os.path.exists(NIUNIU_LENGTHS_FILE):
            with open(NIUNIU_LENGTHS_FILE, 'w', encoding='utf-8') as file:
                yaml.dump({}, file, allow_unicode=True)

    def load_niuniu_lengths(self):
        try:
            with open(NIUNIU_LENGTHS_FILE, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file) or {}
        except FileNotFoundError:
            return {}

    def save_niuniu_lengths(self):
        with open(NIUNIU_LENGTHS_FILE, 'w', encoding='utf-8') as file:
            yaml.dump(self.niuniu_lengths, file, allow_unicode=True)

    @filter.command("注册牛牛")
    async def register_niuniu(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = event.message_obj.group_id
        if group_id:
            if group_id not in self.niuniu_lengths:
                self.niuniu_lengths[group_id] = {}
            if user_id not in self.niuniu_lengths[group_id]:
                # 从配置中获取范围来生成牛牛长度
                config = self.config.get('niuniu_config', {})
                min_length = config.get('min_length', 1)
                max_length = config.get('max_length', 10)
                length = random.randint(min_length, max_length)
                self.niuniu_lengths[group_id][user_id] = length
                self.save_niuniu_lengths()
                await event.plain_result(f"注册成功，你的牛牛现在有{length} cm")
            else:
                await event.plain_result("你已经注册过牛牛啦！")
        else:
            await event.plain_result("该指令仅限群聊中使用。")

    @filter.command("打胶")
    async def dajiao(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = event.message_obj.group_id
        if group_id and group_id in self.niuniu_lengths and user_id in self.niuniu_lengths[group_id]:
            # 从配置中获取范围来确定打胶的变化量
            config = self.config.get('niuniu_config', {})
            min_change = config.get('min_change', -5)
            max_change = config.get('max_change', 5)
            change = random.randint(min_change, max_change)
            if change > 0:
                message = f"你嘿咻嘿咻一下，促进牛牛发育，牛牛增长{change}cm了呢"
            elif change < 0:
                message = f"哎呀，打胶过度，牛牛缩短了{-change}cm呢"
            else:
                message = "这次打胶好像没什么效果哦"
            self.niuniu_lengths[group_id][user_id] += change
            if self.niuniu_lengths[group_id][user_id] < 1:
                self.niuniu_lengths[group_id][user_id] = 1
            self.save_niuniu_lengths()
            await event.plain_result(f"{message}，当前牛牛长度为{self.niuniu_lengths[group_id][user_id]}cm")
        else:
            await event.plain_result("你还没有注册牛牛，请先发送“注册牛牛”进行注册。")

    @filter.command("我的牛牛")
    async def my_niuniu(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = event.message_obj.group_id
        if group_id and group_id in self.niuniu_lengths and user_id in self.niuniu_lengths[group_id]:
            length = self.niuniu_lengths[group_id][user_id]
            await event.plain_result(f"你的牛牛长度为{length} cm")
        else:
            await event.plain_result("你还没有注册牛牛，请先发送“注册牛牛”进行注册。")

    @filter.command("比划比划")
    async def compare_niuniu(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = event.message_obj.group_id
        if group_id and group_id in self.niuniu_lengths and user_id in self.niuniu_lengths[group_id]:
            chain = event.message_obj.message
            at_list = [str(comp.qq) for comp in chain if isinstance(comp, At)]
            if at_list:
                target_user_id = at_list[0]
                if target_user_id in self.niuniu_lengths[group_id]:
                    user_length = self.niuniu_lengths[group_id][user_id]
                    target_length = self.niuniu_lengths[group_id][target_user_id]
                    diff = user_length - target_length
                    if abs(diff) > 10:
                        if diff > 0:
                            # 从配置中获取范围来确定比划胜利后的奖励
                            config = self.config.get('niuniu_config', {})
                            min_bonus = config.get('min_bonus', 0)
                            max_bonus = config.get('max_bonus', 3)
                            bonus = random.randint(min_bonus, max_bonus)
                            self.niuniu_lengths[group_id][user_id] += bonus
                            self.save_niuniu_lengths()
                            await event.plain_result(f"你以绝对的长度令对方屈服了，你的长度增加{bonus}cm ,当前长度{self.niuniu_lengths[group_id][user_id]}cm")
                        else:
                            config = self.config.get('niuniu_config', {})
                            min_bonus = config.get('min_bonus', 0)
                            max_bonus = config.get('max_bonus', 3)
                            bonus = random.randint(min_bonus, max_bonus)
                            self.niuniu_lengths[group_id][target_user_id] += bonus
                            self.save_niuniu_lengths()
                            await event.plain_result(f"对方以绝对的长度令你屈服了，对方长度增加{bonus}cm")
                    else:
                        await event.plain_result("你们的牛牛长度差距不大，继续加油哦！")
                else:
                    await event.plain_result("对方还没有注册牛牛呢！")
            else:
                await event.plain_result("请 @ 一名已注册牛牛的用户进行比划。")
        else:
            await event.plain_result("你还没有注册牛牛，请先发送“注册牛牛”进行注册。")

    @filter.command("牛牛排行")
    async def niuniu_rank(self, event: AstrMessageEvent):
        group_id = event.message_obj.group_id
        if group_id and group_id in self.niuniu_lengths:
            sorted_niuniu = sorted(self.niuniu_lengths[group_id].items(), key=lambda x: x[1], reverse=True)
            rank_message = "牛牛排行榜：\n"
            bot = event.get_bot()  # 假设可以通过 event 获取 bot 对象
            for i, (user_id, length) in enumerate(sorted_niuniu, start=1):
                try:
                    member_info = await bot.get_group_member_info(group_id=int(group_id), user_id=int(user_id))
                    nickname = member_info.get("nickname", "未知用户")
                except Exception as e:
                    nickname = "未知用户"
                rank_message += f"{i}. {nickname}：{length} cm\n"
            await event.plain_result(rank_message)
        else:
            await event.plain_result("当前群里还没有人注册牛牛呢！")
