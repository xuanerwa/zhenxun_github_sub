from arclet.alconna import CommandMeta
from nonebot.plugin import PluginMetadata
from nonebot_plugin_alconna import Alconna, Args, on_alconna
from nonebot_plugin_session import EventSession
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11 import Bot as v11Bot
from nonebot.adapters.onebot.v12 import Bot as v12Bot
from .data_source import (
    add_user_sub,
    SubManager,
    get_sub_status

)
from zhenxun.configs.config import Config, BotConfig
from zhenxun.configs.utils import PluginExtraData, RegisterConfig
from nonebot_plugin_apscheduler import scheduler
from typing import Optional
from zhenxun.services.log import logger
from nonebot import Driver
import nonebot
from zhenxun.utils.message import MessageUtils
from zhenxun.utils.platform import PlatformUtils
from zhenxun.models.group_console import GroupConsole
from .model import GitHubSub

base_config = Config.get("github_sub")

__plugin_meta__ = PluginMetadata(
    name="github订阅",
    description="订阅github用户或仓库",
    usage="""
    usage：
        github新Comment，PR，Issue等提醒
    指令：
        添加github ['用户'/'仓库'] [用户名/{owner/repo}]
        删除github [用户名/{owner/repo}]
        查看github
        示例：添加github订阅 用户 HibiKier
        示例：添加gb订阅 仓库 HibiKier/zhenxun_bot
        示例：添加github 用户 HibiKier
        示例：删除gb订阅 HibiKier
    """.strip(),
    extra=PluginExtraData(
        author="xuanerwa",
        version="0.9",
        configs=[
            RegisterConfig(
                module="github_sub",
                key="GITHUB_TOKEN",
                value=None,
                help="登陆github获取 https://github.com/settings/tokens/new"
            ),
            RegisterConfig(
                module="github_sub",
                key="GITHUB_ISSUE",
                value=True,
                help="是否不推送Issue",
                default_value=True,
                type=bool,
            ),
            RegisterConfig(
                module="github_sub",
                key="CHECK_API_TIME",
                value=30,
                help="github订阅api间隔(秒)",
                default_value=30,
                type=int,
            )
        ],
        admin_level=base_config.get("GROUP_GITHUB_SUB_LEVEL"),
    ).dict(),
)
Config.add_plugin_config(
    "github_sub",
    "GROUP_GITHUB_SUB_LEVEL",
    5,
    help="github订阅需要的管理员等级",
    default_value=5,
    type=int,
)

_add_sub_matcher = on_alconna(
    Alconna("添加github订阅", Args["sub_type", str]["sub_url", str], meta=CommandMeta(compact=True)),
    aliases={"添加github", "添加gb订阅"}, priority=5, block=True)
del_sub = on_alconna(Alconna("删除github订阅", Args["sub_url", str], meta=CommandMeta(compact=True)),
                     aliases={"删除github", "删除gb订阅"}, priority=5, block=True)
show_sub_info = on_alconna(Alconna("查看github订阅"), aliases={"查看github", "查看gb", "查看gb订阅"}, priority=5, block=True)

driver: Driver = nonebot.get_driver()

sub_manager: Optional[SubManager] = None


@driver.on_startup
async def _():
    global sub_manager
    sub_manager = SubManager()


@_add_sub_matcher.handle()
async def _(session: EventSession, sub_type: str, sub_url: str):
    if sub_type == "用户":
        sub_type_str = "user"
    elif sub_type == "仓库":
        sub_type_str = "repository"
    else:
        await MessageUtils.build_message("参数错误，第一参数必须为：用户/仓库！").finish()
    sub_url = (sub_url.strip('/')).strip()
    gid = session.id3 or session.id2
    if gid:
        sub_user = f"{session.id1}:{gid}"
    else:
        sub_user = f"{session.id1}"

    msg = await add_user_sub(sub_type_str, sub_url, sub_user)
    await MessageUtils.build_message(msg).finish()


@del_sub.handle()
async def _(bot: Bot,session: EventSession, sub_url: str):
    gid = session.id3 or session.id2
    if gid:
        if session.id1 in bot.config.superusers:
            sub_user = f":{gid}"
        else:
            sub_user = f"{session.id1}:{gid}"
    else:
        sub_user = f"{session.id1}"

    if await GitHubSub.delete_github_sub(sub_url, sub_user):
        await MessageUtils.build_message(f"删除github订阅：{sub_url} 成功...").send()
        logger.info(
            f"(USER {session.id1}, GROUP "
            f"{gid if gid else 'private'})"
            f" 删除订阅 {sub_user}"
        )
    else:
        await del_sub.send(f"删除订阅：{sub_url} 失败...")


@show_sub_info.handle()
async def _(session: EventSession):
    id_ = session.id3 or session.id2 or f"{session.id1}"
    data = await GitHubSub.filter(sub_users__contains=id_).all()
    user_rst = ""
    repository_rst = ""
    num_user = 1
    num_repository = 1
    for x in data:
        if x.sub_type == "user":
            user_rst += (
                f"\t{num_user}. {x.sub_url}\n"
            )
            num_user += 1
        if x.sub_type == "repository":
            repository_rst += f"\t{num_repository}. {x.sub_url}\n"
            num_repository += 1
    user_rst = "当前订阅的github用户：\n" + user_rst if user_rst else user_rst
    repository_rst = "当前订阅的github仓库：\n" + repository_rst if repository_rst else repository_rst

    if not user_rst and not repository_rst:
        user_rst = (
            "该群目前没有任何订阅..." if session.id3 or session.id2 else "您目前没有任何订阅..."
        )
    await MessageUtils.build_message(user_rst + repository_rst).send()


# 推送
@scheduler.scheduled_job(
    "interval",
    seconds=base_config.get("CHECK_API_TIME") if base_config.get("CHECK_API_TIME") else 30,
)
async def _():
    bots = nonebot.get_bots()
    for bot in bots.values():
        sub = None
        if bot:
            try:
                await sub_manager.reload_sub_data()
                sub = await sub_manager.random_sub_data()
                if sub:
                    logger.info(f"github开始检测：{sub.sub_url}")
                    rst = await get_sub_status(sub.sub_type, sub.sub_url, etag=sub.etag)
                    if isinstance(rst, list) and isinstance(bot, (v11Bot, v12Bot)):
                        await send_sub_msg_list(rst, sub, bot)
                    else:
                        await send_sub_msg(rst, sub, bot)
            except Exception as e:
                logger.error(f"github订阅推送发生错误 sub_url：{sub.sub_url if sub else 0} {type(e)}：{e}")


async def send_sub_msg(rst: str, sub: GitHubSub, bot: Bot):
    """
    推送信息
    :param rst: 回复
    :param sub: GitHubSub
    :param bot: Bot
    """
    if rst:
        for x in sub.sub_users.split(",")[:-1]:
            try:
                if ":" in x:
                    gid = x.split(":")[1]
                    if not await GroupConsole.is_block_plugin(gid, "github_sub"):
                        await PlatformUtils.send_message(bot, None, gid, message=rst)
                else:
                    await PlatformUtils.send_message(bot, x, None, message=rst)
            except Exception as e:
                logger.error(f"github订阅推送发生错误 sub_url：{sub.sub_url} {type(e)}：{e}")


async def send_sub_msg_list(rst_list: list, sub: GitHubSub, bot: Bot):
    """
    推送信息
    :param rst_list: 回复列表
    :param sub: GitHubSub
    :param bot: Bot
    """
    if rst_list:
        for x in sub.sub_users.split(",")[:-1]:
            try:
                mes_list = []
                for img in rst_list:
                    data = {
                        "type": "node",
                        "data": {"name": f"{BotConfig.self_nickname}", "uin": f"{bot.self_id}", "content": img},
                    }
                    mes_list.append(data)
                if ":" in x:
                    gid = x.split(":")[1]
                    if not await GroupConsole.is_block_plugin(gid, "github_sub"):
                        await bot.send_group_forward_msg(
                            group_id=int(x.split(":")[1]), messages=mes_list)
                else:
                    await bot.send_group_forward_msg(user_id=int(x), messages=mes_list)
            except Exception as e:
                logger.error(f"github订阅推送发生错误 sub_url：{sub.sub_url} {type(e)}：{e}")
