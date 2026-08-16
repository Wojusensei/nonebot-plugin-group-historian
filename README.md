# nonebot-plugin-group-historian

✨ 群聊史官 ✨

基于 NoneBot2 的群聊发言统计插件，自动生成每日"话痨榜"图片。

## 功能

- 统计群成员每日发言总字数（仅统计文本中的中文/字母/数字）
- 按发言字数从高到低生成排行榜图片（前三名金色高亮）
- 按日期统计，跨天自动从新一天重新计数
- 超过保留期的旧数据自动清理

## 安装

```bash
nb plugin install nonebot-plugin-group-historian
pip install nonebot-plugin-group-historian
```

## 使用

在群聊中发送以下命令：

- 今日话痨榜：获取今日群内发言字数排行榜（机器人回复图片）

## 配置

默认即装即用，可选配置项（写入 .env 文件）：

```ini
historian_rank_count=10
historian_data_retention_days=30
```

- `historian_rank_count`：排行榜显示人数
- `historian_data_retention_days`：数据保留天数，启动时自动清理更早的数据

## 数据存储

使用 nonebot-plugin-orm（SQLite + aiosqlite）存储，数据库文件自动存放在
nonebot-plugin-localstore 标准数据目录下。

**首次启动**时，nonebot-plugin-orm 会在控制台询问"目标数据库未更新到最新迁移, 是否更新?"，
输入 `y` 回车即可完成建表（也可提前运行 `nb orm upgrade`）。

## 注意事项

- 仅统计文本消息（中文、字母、数字），图片、表情、文件等不计算
- 需要机器人有发送图片的权限
- 话痨榜图片支持自定义：将字体文件命名为 `font.ttf`、背景图命名为 `background.png`
  放入插件数据目录即可（未放置时自动使用系统中文字体与纯色背景）

## 0.2.0 更新日志

修复了导致插件完全不可用的多处缺陷：

- **修复致命 bug**：`async with get_scoped_session()` 直接报 `TypeError`
  （`async_scoped_session` 不是异步上下文管理器），此前一条消息都无法记录、
  排行榜必然报错；改用 `get_session()`
- **修复致命 bug**：ORM 模型类在函数内部重复定义，第二条消息起必然抛
  `InvalidRequestError`；改为模块级 `Model` 定义（符合 nonebot-plugin-orm 规范）
- **修复**：未声明异步数据库驱动 `aiosqlite`，新环境安装后第一条消息即报
  `ModuleNotFoundError`
- **修复**：`migrations/` 目录从未被打包进发行版（缺少 package-data 声明），
  用户安装后无法通过迁移建表
- **修复**：每条消息都调用一次 `get_group_member_info` API 获取昵称（高频触发风控，
  且多 Bot 在线时 `get_bot()` 抛异常）；改为直接读取事件自带的群名片/昵称
- **修复**：Linux 服务器上图片中文显示为方框（自动探测系统中文字体，
  支持自定义 font.ttf）
- **修复**：私聊使用命令无响应（现提示仅支持群聊）
- 启用 `historian_rank_count` 配置（此前声明了但从未生效）
- 接入此前未被引用的图片渲染模块：分页渲染、背景图/自定义字体支持、
  图片直接以 bytes 发送不再落盘；移除无法渲染的 emoji 图标与错误的页脚文案
- `requires-python` 提升至 3.10；新增测试套件（nonebug + pytest，16 例）

## 开发

```bash
pip install -e ".[test]"
pytest
```

## 开源协议

MIT

## 仓库

https://github.com/Wojusensei/nonebot-plugin-group-historian
