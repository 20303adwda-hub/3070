import stripe
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ==========================================
# 1. Stripe 金鑰設定 (請替換為您真實的測試金鑰)
# ==========================================
stripe.api_key = "sk_test_51TBmkYJ0xpZrLz6rXJYheSJ9XoZjotHrmCtNyeBOblHTC72pzYir85PMc549IFAUstK8106Sk6fOoNT25dngQ5Cf00qBUZN41h"          # Stripe Secret Key
# Stripe Webhook Secret (從您剛才提供的訊息)
endpoint_secret = "whsec_zYwjLIct4kWNykDyE0AACXihZORiTPRh"

# ==========================================
# 2. 騰訊雲伺服器設定 (取代以前的 ThingSpeak)
# ==========================================
TENCENT_SERVER_IP = "43.156.92.189"
TENCENT_SERVER_PORT = 8000
WRITE_KEY = "EE3070_WRITE_KEY"

# 假設您的騰訊雲後端接收事件的 API 路徑
TENCENT_API_URL = f"http://{TENCENT_SERVER_IP}:{TENCENT_SERVER_PORT}/api/events"

def notify_tencent_server(msg_type):
    # 加入 device_id 並確保 payload 是一個完整的 JSON 物件
    payload = {
        "device_id": "StripeWebhook",
        "event_type": "cart_scan",
        "payload": {
            "msg_type": msg_type,
            "scan_count": 0
        }
    }

    try:
        response = requests.post(
            f"{TENCENT_API_URL}?write_key={WRITE_KEY}",
            json=payload,
            timeout=5
        )
        # 加上詳細的錯誤列印，方便我們後續除錯
        print(f"Tencent Cloud Sync - Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Tencent Cloud Sync Failed: {e}")

# ==========================================
# 3. Flask 路由設定
# ==========================================
@app.route('/')
def hello_world():
    return "<h1>MATLAB Smart Supermarket Webhook Server is Running!</h1>"

@app.route('/success')
def success():
    # 顧客在手機上付款成功後跳轉的頁面
    # (通常 Webhook 也會觸發，但雙重保險可以在此呼叫)
    notify_tencent_server(5)
    return "<h1>支付成功！</h1><p>請查看收銀台螢幕，您的購物車將自動清空。</p>"

@app.route('/cancel')
def cancel():
    # 顧客在 Stripe 頁面點擊返回或取消支付
    notify_tencent_server(6)
    return "<h1>支付已取消</h1><p>請查看收銀台螢幕並重新選擇支付方式。</p>"

@app.route('/webhook', methods=['POST'])
def webhook():
    # 接收 Stripe 背景發送的非同步付款結果通知
    payload = request.data
    sig_header = request.headers.get('STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({'error': 'Invalid signature'}), 400

    # 如果 Stripe 通知結帳已完成
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        print(f"Payment successful for session: {session.get('id')}")

        # 寫入狀態 5 (成功) 到騰訊雲伺服器
        notify_tencent_server(5)

    return jsonify({'status': 'success'}), 200

import os
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
