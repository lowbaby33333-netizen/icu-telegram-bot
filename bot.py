import os
import time
import threading
from datetime import datetime, timedelta

from dotenv import load_dotenv
import telebot

# .env에서 토큰 불러오기
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN이 .env에 설정되어 있지 않습니다!")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# (chat_id, user_id) -> deadline(UTC 시간)
pending_users = {}

# 제한 시간 (분 단위) - ★ 1분으로 설정 ★
TIME_LIMIT_MINUTES = 1


def utc_now():
    return datetime.utcnow()


def add_pending_user(chat_id: int, user: telebot.types.User):
    """새로 들어온 유저를 인증 대기 목록에 추가"""
    deadline = utc_now() + timedelta(minutes=TIME_LIMIT_MINUTES)
    pending_users[(chat_id, user.id)] = deadline

    name = user.first_name or user.username or "회원님"
    mention = f"<a href='tg://user?id={user.id}'>{name}</a>"

    bot.send_message(
        chat_id,
        (
            "🚨 <b>ICU 신규 환자 입장</b>\n\n"
            f"{mention} 님,\n"
            f"<b>{TIME_LIMIT_MINUTES}분 이내에 현재 포지션 캡쳐(이미지)</b>를 올리지 않으면\n"
            "상태 악화로 ICU 시스템에 의해 <b>자동 강퇴</b>됩니다.\n\n"
            "🛟 구조대를 부르고 싶다면, 지금 바로 포지션 캡쳐를 제출해 주세요."
        ),
    )


@bot.message_handler(content_types=["new_chat_members"])
def handle_new_members(message: telebot.types.Message):
    """새 유저 입장 감지"""
    chat_id = message.chat.id
    for user in message.new_chat_members:
        if user.is_bot:
            continue
        add_pending_user(chat_id, user)


@bot.message_handler(content_types=["photo"])
def handle_photos(message: telebot.types.Message):
    """사진(포지션 캡쳐) 올릴 때 인증 처리"""
    chat_id = message.chat.id
    user = message.from_user
    key = (chat_id, user.id)

    if key in pending_users:
        del pending_users[key]

        name = user.first_name or user.username or "회원님"
        mention = f"<a href='tg://user?id={user.id}'>{name}</a>"

        bot.reply_to(
            message,
            (
                "🟢 <b>ICU 인증 완료</b>\n"
                f"{mention} 님, 구조대 관찰 대상에서 제외되었습니다.\n"
                "이제 자유롭게 채팅하며 관점 공유하시면 됩니다."
            ),
        )


def timeout_worker():
    """제한 시간 지나면 자동 강퇴"""
    while True:
        time.sleep(10)  # 10초마다 확인
        now = utc_now()
        to_kick = []

        for key, deadline in list(pending_users.items()):
            if now > deadline:
                to_kick.append(key)
                del pending_users[key]

        for chat_id, user_id in to_kick:
            try:
                # 강퇴 후 바로 unban 해서 재입장 가능
                bot.kick_chat_member(chat_id, user_id)
                bot.unban_chat_member(chat_id, user_id)

                bot.send_message(
                    chat_id,
                    (
                        "❌ <b>ICU 자동 강퇴</b>\n"
                        f"<a href='tg://user?id={user_id}'>이 사용자</a>는 "
                        f"{TIME_LIMIT_MINUTES}분 안에 포지션 캡쳐를 제출하지 않아 "
                        "ICU에서 자동 퇴원 처리되었습니다."
                    ),
                )
            except Exception as e:
                print(f"[ERROR] 강퇴 실패 chat_id={chat_id}, user_id={user_id}, err={e}")


def main():
    t = threading.Thread(target=timeout_worker, daemon=True)
    t.start()

    print("봇 실행 중... Ctrl + C 로 종료 가능합니다.")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)


if __name__ == "__main__":
    main()
