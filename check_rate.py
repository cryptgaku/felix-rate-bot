"""
Felix Vanilla UBTC/USDH 金利監視Bot
金利がプラスになったらDiscordに通知
"""

import requests
import json
import os
import sys

# ========== 設定 ==========
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
HYPEREVM_RPC = "https://rpc.hyperliquid.xyz/evm"
MORPHO_CONTRACT = "0x68e37de8d93d3496ae143f2e900490f6280c57cd"
MARKET_ID = "0x87272614b7a2022c31ddd7bba8eb21d5ab40a6bcbea671264d59dc732053721d"
RATE_THRESHOLD = 0.0


def scrape_felix_vanilla():
    try:
        url = "https://blue-api.morpho.org/graphql"
        
        query = """
        query {
            markets(
                where: { 
                    chainId_in: [999]
                    uniqueKey_in: ["0x87272614b7a2022c31ddd7bba8eb21d5ab40a6bcbea671264d59dc732053721d"]
                }
            ) {
                items {
                    uniqueKey
                    state {
                        borrowApy
                        supplyApy
                        rewards {
                            borrowApr
                            supplyApr
                        }
                    }
                }
            }
        }
        """
        
        response = requests.post(
            url,
            json={"query": query},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        data = response.json()
        
        if data.get("data", {}).get("markets", {}).get("items"):
            market = data["data"]["markets"]["items"][0]
            state = market.get("state", {})
            
            borrow_apy = float(state.get("borrowApy", 0)) * 100
            
            reward_apr = 0
            for reward in state.get("rewards", []):
                reward_apr += float(reward.get("borrowApr", 0)) * 100
            
            net_rate = borrow_apy - reward_apr
            
            return {
                "borrowApy": borrow_apy,
                "rewardApr": reward_apr,
                "netRate": net_rate
            }
        
        return None
        
    except Exception as e:
        print(f"Morpho API error: {e}")
        return None


def send_discord_notification(net_rate, borrow_apy, reward_apr):
    if not DISCORD_WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK_URL is not set")
        return False
    
    embed = {
        "title": "🚨 Felix金利アラート",
        "description": "**UBTC/USDH の実質金利がプラスになりました！**",
        "color": 0xFF6B6B,
        "fields": [
            {"name": "📊 実質金利（Net Rate）", "value": f"**{net_rate:.2f}%**", "inline": True},
            {"name": "💰 借入金利（Borrow APY）", "value": f"{borrow_apy:.2f}%", "inline": True},
            {"name": "🎁 報酬（Reward APR）", "value": f"-{reward_apr:.2f}%", "inline": True},
            {"name": "⚠️ アクション", "value": "ポジションの解消を検討してください", "inline": False}
        ],
        "footer": {"text": "Felix Vanilla | UBTC担保 → USDH借入"}
    }
    
    response = requests.post(
        DISCORD_WEBHOOK_URL,
        json={"embeds": [embed]},
        headers={"Content-Type": "application/json"}
    )
    
    return response.status_code == 204


def main():
    print("=" * 50)
    print("Felix Vanilla 金利チェック開始")
    print("=" * 50)
    
    rate_data = scrape_felix_vanilla()
    
    if not rate_data:
        print("金利データの取得に失敗しました")
        sys.exit(0)
    
    borrow_apy = rate_data["borrowApy"]
    reward_apr = rate_data["rewardApr"]
    net_rate = rate_data["netRate"]
    
    print(f"借入金利 (Borrow APY): {borrow_apy:.2f}%")
    print(f"報酬 (Reward APR): -{reward_apr:.2f}%")
    print(f"実質金利 (Net Rate): {net_rate:.2f}%")
    
    if net_rate >= RATE_THRESHOLD:
        print("🚨 金利がプラスになりました！通知を送信します...")
        
        success = send_discord_notification(net_rate, borrow_apy, reward_apr)
        
        if success:
            print("✅ Discord通知を送信しました")
            with open("NOTIFICATION_SENT", "w") as f:
                f.write("true")
        else:
            print("❌ Discord通知の送信に失敗しました")
            sys.exit(1)
    else:
        print(f"✅ 金利はまだマイナス ({net_rate:.2f}%) - 監視を継続します")


if __name__ == "__main__":
    main()
