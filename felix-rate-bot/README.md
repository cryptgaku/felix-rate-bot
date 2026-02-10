# Felix 金利監視Bot 🤖

Felix Vanilla（UBTC担保 → USDH借入）の実質金利を監視し、金利がプラスになったらDiscordに通知するbotです。

## 📊 監視内容

- **Borrow APY**: 借入金利
- **Reward APR**: インセンティブ報酬（マイナス金利の原因）
- **Net Rate**: 実質金利（Borrow APY - Reward APR）

Net Rate が 0% 以上になると通知されます。

---

## 🚀 セットアップ手順

### 1. このリポジトリをフォークまたはコピー

1. GitHubで「**New repository**」をクリック
2. リポジトリ名を入力（例: `felix-rate-bot`）
3. 「**Create repository**」をクリック
4. 以下のファイルをアップロード:
   - `check_rate.py`
   - `.github/workflows/check-rate.yml`

### 2. Discord Webhook URLを設定

1. リポジトリの「**Settings**」タブを開く
2. 左メニューから「**Secrets and variables**」→「**Actions**」を選択
3. 「**New repository secret**」をクリック
4. 以下を入力:
   - **Name**: `DISCORD_WEBHOOK_URL`
   - **Secret**: あなたのDiscord Webhook URL
5. 「**Add secret**」をクリック

### 3. GitHub Actionsを有効化

1. リポジトリの「**Actions**」タブを開く
2. 「I understand my workflows, go ahead and enable them」をクリック
3. 左側の「**Felix Rate Monitor**」を選択
4. 「**Enable workflow**」をクリック

### 4. 動作確認（手動実行）

1. 「**Actions**」タブで「**Felix Rate Monitor**」を選択
2. 右側の「**Run workflow**」ボタンをクリック
3. 「**Run workflow**」を確認
4. 実行結果を確認（緑のチェックマークが出ればOK）

---

## ⚙️ 設定のカスタマイズ

### 監視間隔の変更

`.github/workflows/check-rate.yml` の cron 設定を変更:

```yaml
schedule:
  - cron: '*/15 * * * *'  # 15分ごと
  # - cron: '*/30 * * * *'  # 30分ごと
  # - cron: '0 * * * *'     # 1時間ごと
```

### 通知閾値の変更

`check_rate.py` の `RATE_THRESHOLD` を変更:

```python
RATE_THRESHOLD = 0.0   # 0%以上で通知（デフォルト）
# RATE_THRESHOLD = -5.0  # -5%以上で通知
# RATE_THRESHOLD = 1.0   # 1%以上で通知
```

---

## 📱 通知サンプル

金利がプラスになると、以下のような通知がDiscordに届きます:

```
🚨 Felix金利アラート
━━━━━━━━━━━━━━━━━━━
UBTC/USDH の実質金利がプラスになりました！

📊 実質金利（Net Rate）: 1.23%
💰 借入金利（Borrow APY）: 8.50%
🎁 報酬（Reward APR）: -7.27%

⚠️ ポジションの解消を検討してください
```

---

## 🛑 停止方法

### 自動停止
金利がプラスになり通知が送られると、botは自動で停止します。

### 手動停止
1. 「**Actions**」タブを開く
2. 「**Felix Rate Monitor**」を選択
3. 右上の「**...**」→「**Disable workflow**」をクリック

---

## ❓ トラブルシューティング

### 通知が来ない
1. Secretsに `DISCORD_WEBHOOK_URL` が正しく設定されているか確認
2. Actions タブでワークフローが有効か確認
3. 実行ログでエラーがないか確認

### 金利データが取得できない
- Morpho APIまたはHyperEVM RPCが一時的に利用できない可能性があります
- 次回の実行で自動的にリトライされます

---

## 📝 ライセンス

MIT License - 自由にご利用ください。
