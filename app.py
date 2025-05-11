from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from openai import OpenAI

app = Flask(__name__)

# 環境変数から各種キー取得
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Webhookエンドポイント
@app.route("/webhook", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK", 200

# メッセージ受信時の処理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text

    # ChatGPTへ問い合わせ
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # gpt-4 に変更も可能
        messages=[{"role": "user", "content": user_text}]
    )
    reply_text = response.choices[0].message.content

    # LINEに返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# ローカル実行用（Renderでは不要）
if __name__ == "__main__":
    app.run()
