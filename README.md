# nonebot-plugin-group-historian

✨ 群聊史官 ✨

基于 NoneBot2 的群聊发言统计插件，自动生成每日"话痨榜"图片。

## 功能

- 统计群成员每日发言总字数（仅统计纯文本消息）
- 按发言字数从高到低生成排行榜图片
- 每日 00:00 自动重置统计

## 安装

nb plugin install nonebot-plugin-group-historian

或

pip install nonebot-plugin-group-historian

## 使用

在群聊中发送以下命令：

- 今日话痨榜：获取今日群内发言字数排行榜（机器人回复图片）

## 配置

无需配置，即装即用。

## 数据存储

插件使用 nonebot-plugin-localstore 管理数据目录，数据库文件自动存放在标准数据目录下。

## 注意事项

- 仅统计文字消息，图片、表情、文件等不计算
- 排行榜每日 0 点自动重置
- 需要机器人有发送图片的权限
- 少维护，可能有bug

## 开源协议

MIT

## 仓库

https://github.com/Wojusensei/nonebot-plugin-group-historian
