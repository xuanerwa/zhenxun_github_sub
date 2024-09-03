# zhenxun_github_sub

用来推送github用户动态或仓库动态

### 使用

添加github ['用户'/'仓库'] [用户名/{owner/repo}]
删除github [用户名/{owner/repo}]
查看github
示例：添加github订阅用户 HibiKier
示例：添加gb订阅仓库 HibiKier/zhenxun_bot
示例：添加github用户 HibiKier
示例：删除gb订阅 HibiKier

## 更新

**2024/9/3**[v0.9]

1. 修复bug，优化显示
2. 查询api间隔时间修改为默认为30秒

**2024/9/3**[v0.8]

1. 修复bug，超级用户可以删除群内其他人订阅
2. 优化显示
3. 添加设置CHECK_API_TIME，查询api间隔时间，默认为60秒

**2023/2/21**[v0.5]

1. 修复bug，适配最新版真寻

**2022/5/22**

1. 适配真寻最新版

**2022/5/11**[v0.4]

1. 修改删除逻辑

**2022/4/10**[v0.3]

1. 新增推送release
2. 添加设置GITHUB_ISSUE，是否不推送Issue，默认为是

**2022/4/9**[v0.2]

1. 数据库新增etag字段，更新后不设置github token也可推送
2. 之前已部署0.1版本需对真寻发送```exec ALTER TABLE "github_sub" ADD COLUMN "etag" varchar;```

**2022/4/8**[v0.1]

1. 基于真寻beta2开发

