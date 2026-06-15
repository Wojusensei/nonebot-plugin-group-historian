# sql迁移说明

本插件使用py标准库sqlite3进行数据存储，没用SqlAlchemy，Alembic或其他的orm插件，故我这目录应该无需存放任何迁移脚本，数据库表的创建和更新均在插件启动时通过 init_db()函数自动完成（CREATE TABLE IF NOT EXISTS）

若以后引入了ORM我将在此目录提供正式的迁移脚本，感谢提醒awa
