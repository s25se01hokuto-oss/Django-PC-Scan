# ワークスペース構造とコンポーネント概要

**作成日:** 2026年6月23日  
**対象ワークスペース:** `/home/ubuntu/Develop/Django-Ping`  
**ドキュメントID:** 26-06-23_01_Workspace_Overview  

---

## 1. ワークスペース概要 (Workspace Overview)

本ワークスペースは、ローカルネットワーク（LAN）内の教室PCの稼働状況（死活状態）を監視・表示するDjangoベースのWebシステム **「教室PC死活監視システム（classroom-ping / alive-check）」** および関連するネットワーク検証用スクリプト群で構成されています。

### 特徴・コア機能
- **パッシブARPキャッシュ監視**: 監視対象のWindows PC等はファイアウォールによってICMP PingやTCPポート疎通確認を拒否・ドロップするケースが多いため、監視サーバー側のLinuxカーネルARPキャッシュ（`arp -an`）を利用して死活状態を検出します。
- **DBキャッシュ & 非同期同期化**: バックエンドで定期的に動作する管理コマンド（`check_arp`）がARPテーブルを走査してデータベースを更新し、Webビュー（`seat_map_view`）はデータベースから即座に応答を返すことで、Web表示時のロード遅延を最小化しています。
- **サイバーパンク風ダッシュボードUI**: HTML/CSS（CSS Grid）を用い、教室の座席レイアウトに合わせたサイバーパンク/ネオン調のダッシュボードでPCの稼働状況を可視化します。

---

## 2. ディレクトリ構成 (Directory Structure)

```text
/home/ubuntu/Develop/Django-Ping/
├── manage.py                          # Django管理エントリポイント
├── requirements.txt                   # パッケージ依存関係（django>=4.2, markdown>=3.0）
├── db.sqlite3                         # SQLiteデータベース
├── seed_data.py                       # 初期データ（5行×7列の座席グリッド）投入スクリプト
├── arp_cron.log                       # cronジョブ実行ログ（自動生成）
├── walkthrough.md                     # 実装概要・動作確認手順ドキュメント
├── document/                          # ドキュメントディレクトリ（本ファイルを含む）
│   ├── 26-06-08_01_Seat_Map_Implementation_and_Test_Report.md
│   ├── 26-06-08_02_Python-PortScan_Current_Specification.md
│   └── 26-06-23_01_Workspace_Overview.md  [★本書]
├── classroom_ping/                    # Djangoプロジェクト設定ディレクトリ
│   ├── __init__.py
│   ├── settings.py                    # プロジェクト基本設定（アプリケーション登録等）
│   ├── urls.py                        # ルートURLルーティング
│   ├── wsgi.py
│   └── asgi.py
├── alive_check/                       # 死活監視メインアプリケーション
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py                      # データベースモデル（Seat）
│   ├── views.py                       # ビュー処理（座席マップ表示、ドキュメント表示等）
│   ├── urls.py                        # アプリ内ルーティング
│   ├── tests.py
│   ├── templates/                     # テンプレートファイル群
│   │   └── seat_map.html              # 座席マップダッシュボードHTML
│   └── management/                    # Djangoカスタム管理コマンド
│       └── commands/
│           └── check_arp.py           # ARP走査・DB更新コマンド
└── Python-PortScan/                   # スタンドアロン検証用スクリプト群
    ├── arp_check.py                   # ARPキャッシュ検出の単体テストスクリプト
    └── ping_check.py                  # TCP接続型検出の単体テストスクリプト
```

---

## 3. 主要コンポーネント詳細

### 3.1 データベースモデル (`alive_check/models.py`)
座席および通路のレイアウト情報と状態を保持する `Seat` モデルが定義されています。
- **フィールド**:
  - `row` (Integer): グリッドの行インデックス
  - `col` (Integer): グリッドの列インデックス
  - `type` (Char): `seat`（座席）または `aisle`（通路）
  - `ip_address` (GenericIPAddress): 対象PCのIPアドレス（通路はNULL）
  - `status` (Char): `alive`, `dead`, `unknown`
  - `last_checked` (DateTime): 最終確認日時
- **制約**: `(row, col)` の重複を防ぐための `unique_together` ユニーク制約。

### 3.2 コアビューと未実装ビュー (`alive_check/views.py`)
- **`seat_map_view`**: データベースから全座席の情報を読み込み、物理座標 `(row, col)` をテンプレートに合わせたPC名（`pc1`〜`pc20`）にマッピングし、稼働状況を辞書型でテンプレートに渡します。
- **`reports_list_view` / `report_detail_view`**: `document/` ディレクトリ内のMarkdownファイルを読み込み、HTMLに変換して表示するためのビューです。
  - *注意*: これらのレポート表示用ビューは定義されていますが、現在 `alive_check/urls.py` にルーティングが登録されておらず、また対応するテンプレート（`reports_list.html`, `report_detail.html`）も現時点では存在していません。

### 3.3 カスタム管理コマンド (`alive_check/management/commands/check_arp.py`)
- コマンド `python manage.py check_arp` で実行可能。
- `arp -an` を実行してOSのARPテーブルを読み込み、応答が得られているIPのリストを抽出。
- データベース上のすべての `Seat` について、該当IPがARPテーブルで有効なMACアドレスを保持しているかを確認し、`status` フィールドおよび `last_checked` を更新します。

### 3.4 スタンドアロン検証スクリプト (`Python-PortScan/`)
- **`arp_check.py`**: ローカルARPテーブルを読み込み、指定IPが生存しているかを判定するテストスクリプト。
- **`ping_check.py`**: 指定IPの特定のTCPポート（初期設定は135: RPC）にTCP接続を試みるテストスクリプト。ファイアウォールによる接続拒否やドロップ動作の確認用として保存されています。

---

## 4. 動作フロー

```
[サーバー側 cron (5分毎)]
       │
       ▼
`manage.py check_arp` を実行
       │
       ├───► 1. `arp -an` を実行して稼働中IPアドレスのリストを抽出
       │
       └───► 2. DB (db.sqlite3) の `Seat.status` を更新
  
[ユーザーブラウザ (5秒毎自動更新)]
       │
       ▼
`seat_map_view` がDBのキャッシュ状態を即座に読み込み、
『seat_map.html』を用いてサイバーパンク調ネオンカラーUIで可視化して応答
```

---

## 5. 初期データとテスト

- **`seed_data.py`** を実行することで、5行×7列（合計35スロット、PC1〜PC14および通路を含むレイアウト）の動作確認用モックデータがデータベースに登録されます。
- IPアドレスはテスト用に `127.0.0.1` (生存PC) や `192.0.2.x` (オフラインPC) が割り当てられます。
