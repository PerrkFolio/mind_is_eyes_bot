import configparser

path = "C:\\Users\\User\\WebstormProjects\\admin-bot.jaristo-cyber-room.ru\\bot\\configs\\main.ini"
config = configparser.ConfigParser()
config.add_section("SECRET")
config.set("SECRET", "token", "OTU4MDI4NDczNTY4NDY0OTY2.GBKjbs.yc-CiCZYh6RdGySPfWBbL9g9KLr5IIEH_nHLO0")
config.add_section("BOT")
config.set("BOT", "bot_description", "Описание")
config.set("BOT", "bot_prefix", "!")
config.add_section("LOGGING")
config.set("LOGGING", "log_name", "app")
config.set("LOGGING", "log_path", "logs/app.log")
config.set("LOGGING", "log_level", "debug")
config.add_section("ERROR_MSG")
config.set("ERROR_MSG", "error_checkfailure", "***Вы не имеете прав для использования этой команды!***")
config.set("ERROR_MSG", "error_commandnotfound", "***Такой команды нет!***")
config.set("ERROR_MSG", "error_missingrequiredargument", "***Неверно введена команда!***")
config.set("ERROR_MSG", "error_badargument", "***Неверно введена команда!***")

with open(path, "w") as config_file:
    config.write(config_file)
