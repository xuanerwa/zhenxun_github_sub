from datetime import datetime
from typing import List, Optional
from tortoise import fields
from zhenxun.services.db_context import Model
from zhenxun.services.log import logger


class GitHubSub(Model):
    id = fields.IntField(pk=True, generated=True, auto_increment=True)
    """自增id"""
    sub_type = fields.CharField(255)
    """订阅类型"""
    sub_users = fields.TextField()
    """订阅用户"""
    sub_url = fields.CharField(255)
    """订阅地址"""
    update_time = fields.DatetimeField(null=True)
    """更新日期"""
    etag = fields.CharField(255, null=True)
    """etag字段"""

    class Meta:
        table = "github_sub"
        table_description = "github订阅数据表"
        unique_together = ("sub_type", "sub_url")

    @classmethod
    async def update_github_sub(
            cls,
            sub_url: Optional[str] = None,
            *,
            sub_type: Optional[str] = None,
            sub_user: str = "",
            update_time: Optional[datetime] = None,
            etag: Optional[str] = None,
    ) -> bool:
        """
        说明：
            添加订阅
        参数：
            :param sub_url: 订阅地址
            :param sub_type: 订阅类型
            :param sub_user: 订阅此条目的用户
            :param update_time: 订阅更新日期
            :param etag: etag字段
        """
        data = {
            "sub_type": sub_type,
            "sub_user": sub_user,
            "sub_url": sub_url,
            "update_time": update_time,
            "etag": etag}
        if sub_user:
            sub_user = sub_user if sub_user[-1] == "," else f"{sub_user},"
        sub = None
        if sub_type:
            sub = await cls.get_or_none(sub_url=sub_url, sub_type=sub_type)
        else:
            sub = await cls.get_or_none(sub_url=sub_url)
        if sub:
            sub_users = sub.sub_users + sub_user
            data["sub_type"] = sub_type or sub.sub_type
            data["sub_url"] = sub_url or sub.sub_url
            data["sub_users"] = sub_users
            data["update_time"] = update_time or sub.update_time
            data["etag"] = etag or sub.etag
        else:
            await cls.create(sub_url=sub_url, sub_type=sub_type, sub_users=sub_user, update_time=update_time)
        await cls.update_or_create(sub_url=sub_url, defaults=data)
        return True

    @classmethod
    async def delete_github_sub(cls, sub_url: str, sub_user: str) -> bool:
        """
        说明：
            删除订阅
        参数：
            :param sub_url: 订阅地址
            :param sub_user: 删除此条目的用户
        """
        try:
            sub = await cls.filter(
                sub_url=sub_url, sub_users__contains=sub_user
            ).first()
            if not sub:
                return False

            sub_users_list = sub.sub_users.split(',')

            if sub_user.startswith(':'):
                # 删除 "user_id:sub_user_id" 形式
                sub_users_list = [
                    user for user in sub_users_list 
                    if not user.endswith(sub_user)
                ]
            else:
                # 删除完整的 "user_id" 或 "user_id:sub_user_id"
                sub_users_list = [
                    user for user in sub_users_list 
                    if user != sub_user and not user.startswith(f"{sub_user}:")
                ]

            sub.sub_users = ','.join(sub_users_list)

            if sub.sub_users.strip():
                await sub.save(update_fields=["sub_users"])
            else:
                await sub.delete()
                
            return True
        except Exception as e:
            logger.info(f"github_sub 删除订阅错误 {type(e)}: {e}")
            return False
    # async def delete_github_sub(cls, sub_url: str, sub_user: str) -> bool:
    #     """
    #     说明：
    #         删除订阅
    #     参数：
    #         :param sub_url: 订阅地址
    #         :param sub_user: 删除此条目的用户
    #     """
    #     try:
    #         sub = await cls.filter(
    #             sub_url=sub_url, sub_users__contains=sub_user
    #         ).first()
    #         if not sub:
    #             return False
    #         sub.sub_users = sub.sub_users.replace(f"{sub_user},", "")
    #         if sub.sub_users.strip():
    #             await sub.save(update_fields=["sub_users"])
    #         else:
    #             await sub.delete()
    #         return True
    #     except Exception as e:
    #         logger.info(f"github_sub 删除订阅错误 {type(e)}: {e}")
    #         return False

    @classmethod
    async def get_all_sub_data(
            cls,
    ) -> "List[GitHubSub], List[GitHubSub]": # type: ignore
        """
        说明：
            分类获取所有数据
        """
        user_data = []
        repository_data = []
        query = await cls.all()
        for x in query:
            if x.sub_type == "user":
                user_data.append(x)
            if x.sub_type == "repository":
                repository_data.append(x)
        return user_data, repository_data
