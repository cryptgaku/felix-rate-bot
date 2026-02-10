"""
Felix Vanilla UBTC/USDH 金利監視Bot
金利がプラスになったらDiscordに通知
"""

import requests
import json
import os
import sys

# ========== 設定 ==========
# Discord Webhook URL（GitHub Secretsから取得）
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# HyperEVM RPC
HYPEREVM_RPC = "https://rpc.hyperliquid.xyz/evm"

# Morphoコントラクト（HyperEVM）
MORPHO_CONTRACT = "0x68e37de8d93d3496ae143f2e900490f6280c57cd"

# UBTC/USDH マーケットID
MARKET_ID = "0x87272614b7a2022c31ddd7bba8eb21d5ab40a6bcbea671264d59dc732053721d"

# 金利の閾値（0% = プラスになったら通知）
RATE_THRESHOLD = 0.0


def get_market_data():
    """
    Morphoコントラクトからマーケットデータを取得
    """
    # market(Id id) の関数セレクタ
    # returns (totalSupplyAssets, totalSupplyShares, totalBorrowAssets, totalBorrowShares, lastUpdate, fee)
    function_selector = "0x3b519fb2"  # market(bytes32)
    
    # マーケットIDをパディング
    market_id_padded = MARKET_ID[2:] if MARKET_ID.startswith("0x") else MARKET_ID
    
    call_data = function_selector + market_id_padded.zfill(64)
    
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{
            "to": MORPHO_CONTRACT,
            "data": call_data
        }, "latest"],
        "id": 1
    }
    
    response = requests.post(HYPEREVM_RPC, json=payload)
    result = response.json()
    
    if "result" in result and result["result"] != "0x":
        data = result["result"][2:]  # 0xを除去
        
        # 各値を解析（各32バイト = 64文字）
        total_supply_assets = int(data[0:64], 16)
        total_supply_shares = int(data[64:128], 16)
        total_borrow_assets = int(data[128:192], 16)
        total_borrow_shares = int(data[192:256], 16)
        last_update = int(data[256:320], 16)
        fee = int(data[320:384], 16)
        
        return {
            "totalSupplyAssets": total_supply_assets,
            "totalBorrowAssets": total_borrow_assets,
            "lastUpdate": last_update,
            "fee": fee
        }
    
    return None


def fetch_felix_page_data():
    """
    Felix公式ページからAPIデータを取得する代替方法
    Morpho APIがHyperEVMをサポートしていない場合のフォールバック
    """
    try:
        # DefiLlamaからFelix Vanillaの金利を取得
        response = requests.get(
            "https://yields.llama.fi/pools",
            timeout=30
        )
        data = response.json()
        
        # Felix UBTC/USDHプールを検索
        for pool in data.get("data", []):
            if "felix" in pool.get("project", "").lower():
                if "ubtc" in pool.get("symbol", "").lower() and "usdh" in pool.get("underlyingTokens", []):
                    return {
                        "borrowApy": pool.get("apyBorrow", 0),
                        "rewardApr": pool.get("apyReward", 0),
                        "netApy": pool.get("apy", 0)
                    }
        
        return None
    except Exception as e:
        print(f"DefiLlama API error: {e}")
        return None


def scrape_felix_vanilla():
    """
    Felix Vanilla借入金利をWebスクレイピングで取得
    """
    try:
        # Morpho HyperEVM API（Felixが使用）
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
            
            borrow_apy = float(state.get("borrowApy", 0)) * 100  # パーセントに変換
            
            # リワードAPRを集計
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
    """
    Discord Webhookで通知を送信
    """
    if not DISCORD_WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK_URL is not set")
        return False
    
    embed = {
        "title": "🚨 Felix金利アラート",
        "description": "**UBTC/USDH の実質金利がプラスになりました！**",
        "color": 0xFF6B6B,  # 赤色
        "fields": [
            {
                "name": "📊 実質金利（Net Rate）",
                "value": f"**{net_rate:.2f}%**",
                "inline": True
            },
            {
                "name": "💰 借入金利（Borrow APY）",
                "value": f"{borrow_apy:.2f}%",
                "inline": True
            },
            {
                "name": "🎁 報酬（Reward APR）",
                "value": f"-{reward_apr:.2f}%",
                "inline": True
            },
            {
                "name": "⚠️ アクション",
                "value": "ポジションの解消を検討してください",
                "inline": False
            }
        ],
        "footer": {
            "text": "Felix Vanilla | UBTC担保 → USDH借入"
        }
    }
    
    payload = {
        "embeds": [embed]
    }
    
    response = requests.post(
        DISCORD_WEBHOOK_URL,
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    return response.status_code == 204


def main():
    print("=" * 50)
    print("Felix Vanilla 金利チェック開始")
    print("=" * 50)
    
    # 金利データを取得
    rate_data = scrape_felix_vanilla()
    
    if not rate_data:
        print("⚠️ 金利データの取得に失敗しました")
        # 失敗しても継続（次回の実行で再試行）
        sys.exit(0)
    
    borrow_apy = rate_data["borrowApy"]
    reward_apr = rate_data["rewardApr"]
    net_rate = rate_data["netRate"]
    
    print(f"借入金利 (Borrow APY): {borrow_apy:.2f}%")
    print(f"報酬 (Reward APR): -{reward_apr:.2f}%")
    print(f"実質金利 (Net Rate): {net_rate:.2f}%")
    print("-" * 50)
    
    # 金利がプラスかチェック
    if net_rate >= RATE_THRESHOLD:
        print("🚨 金利がプラスになりました！通知を送信します...")
        
        success = send_discord_notification(net_rate, borrow_apy, reward_apr)
        
        if success:
            print("✅ Discord通知を送信しました")
            # 通知成功をマーク（GitHub Actionsを停止するためのフラグ）
            with open("NOTIFICATION_SENT", "w") as f:
                f.write("true")
        else:
            print("❌ Discord通知の送信に失敗しました")
            sys.exit(1)
    else:
        print(f"✅ 金利はまだマイナス ({net_rate:.2f}%) - 監視を継続します")


if __name__ == "__main__":
    main()
