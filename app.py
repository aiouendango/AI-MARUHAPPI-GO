from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from openai import OpenAI

app = Flask(__name__)

# 環境変数からキーを取得
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

# メッセージ受信時の処理（GPT-4o + まるは仕様）
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "あなたは『まるは食堂』のAI専属AIコンシェルジュです。"
                    "南知多の観光名所として有名な『ジャンボエビフライ』や、"
                    "、活魚料理、温泉や回転寿司などなど…"
                    "まるは食堂グループの魅力をお客様に親切で丁寧に、"
                    "わかりやすく案内してください。"
                    "質問に応じて最適な提案をすることが求められます。"
                )
            },
            {
                "role": "user",
                "content": user_text
            }
        ]
    )

    reply_text = response.choices[0].message.content

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# ローカル実行用
if __name__ == "__main__":
    app.run()
