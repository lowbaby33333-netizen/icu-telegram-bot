import telebot
import os

# Render에 BOT_TOKEN 환경변수로 넣을 거야
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "ICU 포지션 인증 봇 작동 중 👀")


if __name__ == "__main__":
    bot.polling(none_stop=True)
