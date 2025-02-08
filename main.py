import random
import yaml
import os
import json
import logging
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import At
from typing import List
from astrbot.api.message_components import BaseMessageComponent

# 定义 YAML 文件路径
NIUNIU_LENGTHS_FILE = 'niuniu_lengths.yml'

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@register("niuniu_plugin", "作者名", "牛牛插件，包含注册牛牛、打胶、我的牛牛、比划比划、牛牛排行等功能", "1.0.0")
class NiuniuPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.niuniu_lengths = self._load_niuniu_lengths()
        logger.info(f"插件配置: {self.config}")

    def _create_niuniu_lengths_file(self):
        """创建 niuniu_lengths.yml 文件"""
        try:
            if not os.path.exists(NIUNIU_LENGTHS_FILE):
                with open(NIUNIU_LENGTHS_FILE, 'w', encoding='utf-8') as file:
                    yaml.dump({}, file, allow_unicode=True)
                logger.info(f"成功创建 {NIUNIU_LENGTHS_FILE} 文件")
        except Exception as e:
            logger.error(f"创建 {NIUNIU_LENGTHS_FILE} 文件时出错: {e}", exc_info=True)

    def _load_niuniu_lengths(self):
        """从 YAML 文件中加载牛牛长度数据"""
        self._create_niuniu_lengths_file()
        try:
            with open(NIUNIU_LENGTHS_FILE, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file) or {}
        except FileNotFoundError:
            logger.warning(f"{NIUNIU_LENGTHS_FILE} 文件未找到，将使用空数据")
            return {}
        except Exception as e:
            logger.error(f"加载 {NIUNIU_LENGTHS_FILE} 文件时出错: {e}", exc_info=True)
            return {}

    def _save_niuniu_lengths(self):
        """将牛牛长度数据保存到 YAML 文件"""
        try:
            with open(NIUNIU_LENGTHS_FILE, 'w', encoding='utf-8') as file:
                yaml.dump(self.niuniu_lengths, file, allow_unicode=True)
            logger.info(f"成功保存数据到 {NIUNIU_LENGTHS_FILE} 文件")
        except Exception as e:
            logger.error(f"保存数据到 {NIUNIU_LENGTHS_FILE} 文件时出错: {e}", exc_info=True)

    @filter.command("注册牛牛")
    async def register_niuniu(self, event: AstrMessageEvent):
        """注册牛牛指令处理函数"""
        try:
            user_id = str(event.get_sender_id())
            group_id = event.message_obj.group_id
            if group_id:
                if group_id not in self.niuniu_lengths:
                    self.niuniu_lengths[group_id] = {}
                if user_id not in self.niuniu_lengths[group_id]:
                    config = self.config.get('niuniu_config', {})
                    min_length = config.get('min_length', 1)
                    max_length = config.get('max_length', 10)
                    length = random.randint(min_length, max_length)
                    self.niuniu_lengths[group_id][user_id] = length
                    self._save_niuniu_lengths()
                    await event.plain_result(f"注册成功，你的牛牛现在有{length} cm")
                else:
                    await event.plain_result("你已经注册过牛牛啦！")
            else:
                await event.plain_result("该指令仅限群聊中使用。")
        except Exception as e:
            logger.error(f"处理 '注册牛牛' 指令时出错: {e}", exc_info=True)

    @filter.command("打胶")
    async def dajiao(self, event: AstrMessageEvent):
        """打胶指令处理函数"""
        try:
            user_id = str(event.get_sender_id())
            group_id = event.message_obj.group_id
            if group_id and group_id in self.niuniu_lengths and user_id in self.niuniu_lengths[group_id]:
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
                self._save_niuniu_lengths()
                await event.plain_result(f"{message}，当前牛牛长度为{self.niuniu_lengths[group_id][user_id]}cm")
            else:
                await event.plain_result("你还没有注册牛牛，请先发送“注册牛牛”进行注册。")
        except Exception as e:
            logger.error(f"处理 '打胶' 指令时出错: {e}", exc_info=True)

    @filter.command("我的牛牛")
    async def my_niuniu(self, event: AstrMessageEvent):
        """我的牛牛指令处理函数"""
        try:
            user_id = str(event.get_sender_id())
            group_id = event.message_obj.group_id
            if group_id and group_id in self.niuniu_lengths and user_id in self.niuniu_lengths[group_id]:
                length = self.niuniu_lengths[group_id][user_id]
                await event.plain_result(f"你的牛牛长度为{length} cm")
            else:
                await event.plain_result("你还没有注册牛牛，请先发送“注册牛牛”进行注册。")
        except Exception as e:
            logger.error(f"处理 '我的牛牛' 指令时出错: {e}", exc_info=True)

    @filter.command("比划比划")
    async def compare_niuniu(self, event: AstrMessageEvent):
        """比划比划指令处理函数"""
        try:
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
                                config = self.config.get('niuniu_config', {})
                                min_bonus = config.get('min_bonus', 0)
                                max_bonus = config.get('max_bonus', 3)
                                bonus = random.randint(min_bonus, max_bonus)
                                self.niuniu_lengths[group_id][user_id] += bonus
                                self._save_niuniu_lengths()
                                await event.plain_result(f"你以绝对的长度令对方屈服了，你的长度增加{bonus}cm ,当前长度{self.niuniu_lengths[group_id][user_id]}cm")
                            else:
                                config = self.config.get('niuniu_config', {})
                                min_bonus = config.get('min_bonus', 0)
                                max_bonus = config.get('max_bonus', 3)
                                bonus = random.randint(min_bonus, max_bonus)
                                self.niuniu_lengths[group_id][target_user_id] += bonus
                                self._save_niuniu_lengths()
                                await event.plain_result(f"对方以绝对的长度令你屈服了，对方长度增加{bonus}cm")
                        else:
                            await event.plain_result("你们的牛牛长度差距不大，继续加油哦！")
                    else:
                        await event.plain_result("对方还没有注册牛牛呢！")
                else:
                    await event.plain_result("请 @ 一名已注册牛牛的用户进行比划。")
            else:
                await event.plain_result("你还没有注册牛牛，请先发送“注册牛牛”进行注册。")
        except Exception as e:
            logger.error(f"处理 '比划比划' 指令时出错: {e}", exc_info=True)

    @filter.command("牛牛排行")
    async def niuniu_rank(self, event: AstrMessageEvent):
        """牛牛排行指令处理函数"""
        try:
            group_id = event.message_obj.group_id
            if group_id and group_id in self.niuniu_lengths:
                sorted_niuniu = sorted(self.niuniu_lengths[group_id].items(), key=lambda x: x[1], reverse=True)
                rank_message = "牛牛排行榜：\n"
                bot = event.get_bot()
                for i, (user_id, length) in enumerate(sorted_niuniu, start=1):
                    try:
                        member_info = await bot.get_group_member_info(group_id=int(group_id), user_id=int(user_id))
                        nickname = member_info.get("nickname", "未知用户")
                    except Exception as e:
                        logger.warning(f"获取用户 {user_id} 信息时出错: {e}", exc_info=True)
                        nickname = "未知用户"
                    rank_message += f"{i}. {nickname}：{length} cm\n"
                await event.plain_result(rank_message)
            else:
                await event.plain_result("当前群里还没有人注册牛牛呢！")
        except Exception as e:
            logger.error(f"处理 '牛牛排行' 指令时出错: {e}", exc_info=True)
