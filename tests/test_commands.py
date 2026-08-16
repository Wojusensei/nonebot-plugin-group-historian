"""命令与消息记录测试（nonebug）"""
import nonebot_plugin_group_historian as plugin
from nonebot.adapters.onebot.v11 import Bot as OB11Bot, Message
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent, Sender

from nonebot_plugin_group_historian import historian_cmd


def make_group_event(text: str, group_id: int = 10000, user_id: int = 20000,
                     card: str = None, nickname: str = "昵称") -> GroupMessageEvent:
    return GroupMessageEvent(
        time=1122,
        self_id=1,
        post_type="message",
        sub_type="normal",
        user_id=user_id,
        message_type="group",
        message_id=1234,
        message=Message(text),
        raw_message=text,
        font=0,
        sender=Sender(user_id=user_id, nickname=nickname, card=card),
        group_id=group_id,
    )


def make_private_event(text: str, user_id: int = 20000) -> PrivateMessageEvent:
    return PrivateMessageEvent(
        time=1122,
        self_id=1,
        post_type="message",
        sub_type="friend",
        user_id=user_id,
        message_type="private",
        message_id=1234,
        message=Message(text),
        raw_message=text,
        font=0,
        sender=Sender(user_id=user_id, nickname="test"),
    )


class TestRecorder:
    async def test_records_text_with_nickname(self, app, monkeypatch):
        """回归：昵称应取自事件 sender，不再逐条调用 get_group_member_info API"""
        calls = []

        async def fake_add(group_id, user_id, nickname, length):
            calls.append((group_id, user_id, nickname, length))

        monkeypatch.setattr(plugin, "add_message", fake_add)

        async with app.test_matcher() as ctx:
            adapter = ctx.create_adapter()
            bot = ctx.create_bot(adapter=adapter, base=OB11Bot)
            event = make_group_event("大家好 hello 123", card="群名片A")
            ctx.receive_event(bot, event)

        assert calls == [("10000", "20000", "群名片A", 3 + 5 + 3)]

    async def test_card_fallback_to_nickname(self, app, monkeypatch):
        calls = []

        async def fake_add(group_id, user_id, nickname, length):
            calls.append((group_id, user_id, nickname, length))

        monkeypatch.setattr(plugin, "add_message", fake_add)

        async with app.test_matcher() as ctx:
            adapter = ctx.create_adapter()
            bot = ctx.create_bot(adapter=adapter, base=OB11Bot)
            event = make_group_event("哈喽", card="", nickname="QQ昵称B")
            ctx.receive_event(bot, event)

        assert calls == [("10000", "20000", "QQ昵称B", 2)]

    async def test_skips_command_messages(self, app, monkeypatch):
        calls = []

        async def fake_add(group_id, user_id, nickname, length):
            calls.append((group_id, user_id, nickname, length))

        async def fake_ranking(group_id, date=None):
            return []

        monkeypatch.setattr(plugin, "add_message", fake_add)
        monkeypatch.setattr(plugin, "get_daily_ranking", fake_ranking)

        async with app.test_matcher() as ctx:
            adapter = ctx.create_adapter()
            bot = ctx.create_bot(adapter=adapter, base=OB11Bot)
            # 命令消息本身会触发命令回复（无数据），但不应被记录器计数
            e1 = make_group_event("/今日话痨榜")
            ctx.receive_event(bot, e1)
            ctx.should_call_send(e1, "今天还没有人发言哦～", result=None, bot=bot)
            # 裸“话痨榜”在默认 command_start={"/"}下不触发命令，也不应被记录
            ctx.receive_event(bot, make_group_event("话痨榜"))
            # 其他插件命令（本插件未注册）不触发任何回复
            ctx.receive_event(bot, make_group_event("/help"))

        assert calls == []

    async def test_skips_private_and_empty(self, app, monkeypatch):
        calls = []

        async def fake_add(group_id, user_id, nickname, length):
            calls.append((group_id, user_id, nickname, length))

        monkeypatch.setattr(plugin, "add_message", fake_add)

        async with app.test_matcher() as ctx:
            adapter = ctx.create_adapter()
            bot = ctx.create_bot(adapter=adapter, base=OB11Bot)
            ctx.receive_event(bot, make_private_event("私聊消息"))
            ctx.receive_event(bot, make_group_event("[CQ:image,file=a.jpg]"))

        assert calls == []


class TestHistorianCommand:
    async def test_private_gets_reply(self, app):
        """回归：私聊使用命令应得到提示，而不是无响应"""
        async with app.test_matcher() as ctx:
            adapter = ctx.create_adapter()
            bot = ctx.create_bot(adapter=adapter, base=OB11Bot)
            event = make_private_event("/今日话痨榜")
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, "该命令仅支持群聊", result=None, bot=bot)
            ctx.should_finished(historian_cmd)

    async def test_no_data_today(self, app, monkeypatch):
        async def fake_ranking(group_id, date=None):
            return []

        monkeypatch.setattr(plugin, "get_daily_ranking", fake_ranking)

        async with app.test_matcher() as ctx:
            adapter = ctx.create_adapter()
            bot = ctx.create_bot(adapter=adapter, base=OB11Bot)
            event = make_group_event("/今日话痨榜")
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, "今天还没有人发言哦～", result=None, bot=bot)
            ctx.should_finished(historian_cmd)

    async def test_success_no_extra_error(self, app, monkeypatch):
        """回归：成功回复后不应再追加报错（FinishedException 被 except 吞）"""
        async def fake_ranking(group_id, date=None):
            return [("1", "甲", 100), ("2", "乙", 50)]

        def fake_image(ranking, page=1, rank_count=10):
            return b"fakepng"

        monkeypatch.setattr(plugin, "get_daily_ranking", fake_ranking)

        from nonebot_plugin_group_historian import image as image_mod
        monkeypatch.setattr(image_mod, "create_ranking_image", fake_image)

        class FakeSegment:
            @staticmethod
            def image(data):
                return "IMAGE_SENT"

        monkeypatch.setattr(plugin, "MessageSegment", FakeSegment)

        async with app.test_matcher() as ctx:
            adapter = ctx.create_adapter()
            bot = ctx.create_bot(adapter=adapter, base=OB11Bot)
            event = make_group_event("/今日话痨榜")
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, "IMAGE_SENT", result=None, bot=bot)
            ctx.should_call_send(event, "以上是今日话痨榜", result=None, bot=bot)
            ctx.should_finished(historian_cmd)

    async def test_db_error_single_reply(self, app, monkeypatch):
        async def fake_ranking(group_id, date=None):
            raise RuntimeError("db boom")

        monkeypatch.setattr(plugin, "get_daily_ranking", fake_ranking)

        async with app.test_matcher() as ctx:
            adapter = ctx.create_adapter()
            bot = ctx.create_bot(adapter=adapter, base=OB11Bot)
            event = make_group_event("/今日话痨榜")
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, "获取话痨榜失败，请稍后再试", result=None, bot=bot)
            ctx.should_finished(historian_cmd)
