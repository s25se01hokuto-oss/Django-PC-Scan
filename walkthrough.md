# 教室PC死活監視システム 実装ドキュメント (Walkthrough)

Djangoを使用した「教室PC死活監視システム（alive-check system）」のバックエンド実装が完了しました。本ドキュメントでは、各モジュールの詳細、非同期（並列）ping処理の仕組み、および動作検証結果についてまとめます。

---

## 📂 プロジェクトのフォルダ構成

作成された主要なファイルと配置場所は以下の通りです。

```text
/home/ubuntu/Develop/Django-Ping/
├── requirements.txt         # 依存関係定義 (Django >= 4.2)
├── seed_data.py             # 動作確認用初期データ投入スクリプト
├── manage.py
├── classroom_ping/          # プロジェクト設定ディレクトリ
│   ├── settings.py          # アプリ登録と基本設定
│   └── urls.py              # ルートURLルーティング定義
└── alive_check/             # 監視機能アプリケーション
    ├── models.py            # Seat（座席/通路）モデル
    ├── views.py             # 非同期並列ping処理ビュー
    ├── urls.py              # アプリケーション個別ルーティング定義
    └── templates/
        └── seat_map.html    # グラスモルフィズム風ダッシュボード UI
```

---

## 🛠️ 各ファイルのコード詳細

### 1. データベースモデル (`Seat`)
- **配置先**: [alive_check/models.py](file:///home/ubuntu/Develop/Django-Ping/alive_check/models.py)

座席レイアウトを柔軟に管理するため、行（`row`）・列（`col`）・タイプ（`type`）・IPアドレス（`ip_address`）を持つ `Seat` モデルを実装しました。また、同一グリッド位置に重複してデータを登録できないよう、`(row, col)` の複合ユニーク制約を付与しています。

```python
from django.db import models

class Seat(models.Model):
    TYPE_CHOICES = [
        ('seat', 'Seat'),   # 座席
        ('aisle', 'Aisle'), # 通路
    ]

    row = models.IntegerField()
    col = models.IntegerField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['row', 'col']
        unique_together = ('row', 'col')

    def __str__(self):
        if self.type == 'seat':
            return f"Seat ({self.row}, {self.col}) - {self.ip_address or 'No IP'}"
        return f"Aisle ({self.row}, {self.col})"
```

### 2. 非同期並列pingビュー (`seat_map_view`)
- **配置先**: [alive_check/views.py](file:///home/ubuntu/Develop/Django-Ping/alive_check/views.py)

ページのロード時に発生する遅延を最小化するため、Pythonの `asyncio` を用いて、IPアドレスが登録されている全ての座席に対して並列に `ping -c 1 -W 1 [IP]` を実行します。
- `sync_to_async` を用いて、Django ORM経由のデータベース読み込みを非同期コンテキストで安全に行います。
- `asyncio.gather` を使用して、すべての ping 送信タスクを一斉に並列実行します。

```python
import asyncio
from django.shortcuts import render
from asgiref.sync import sync_to_async
from .models import Seat

async def ping_ip(ip):
    if not ip:
        return 'dead'
    try:
        # ping -c 1 -W 1 [IP] を非同期サブプロセスで実行
        proc = await asyncio.create_subprocess_exec(
            'ping', '-c', '1', '-W', '1', ip,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        # プロセスのハング防止のため最大1.5秒でタイムアウト設定
        await asyncio.wait_for(proc.wait(), timeout=1.5)
        return 'alive' if proc.returncode == 0 else 'dead'
    except Exception:
        return 'dead'

@sync_to_async
def get_all_seats():
    # 評価済みのリストとして返すことで、非同期スレッド内での遅延評価エラーを防ぐ
    return list(Seat.objects.all().order_by('row', 'col'))

async def seat_map_view(request):
    seats = await get_all_seats()

    # pingを実行する対象座席のタスクリストを作成
    ping_tasks = []
    ip_seats = []
    for seat in seats:
        if seat.type == 'seat' and seat.ip_address:
            ping_tasks.append(ping_ip(seat.ip_address))
            ip_seats.append(seat)

    # 全てのpingを並列に同時実行
    statuses = await asyncio.gather(*ping_tasks) if ping_tasks else []

    # 各座席IDとping結果のステータスをマッピング
    seat_status_map = {}
    for idx, seat in enumerate(ip_seats):
        seat_status_map[seat.id] = statuses[idx]

    # 行ごとにグループ化した2次元配列 (マトリックス) を作成
    from collections import defaultdict
    matrix_dict = defaultdict(list)
    for seat in seats:
        seat_data = {
            "type": seat.type,
        }
        if seat.type == 'seat':
            seat_data["ip"] = seat.ip_address
            if seat.ip_address:
                seat_data["status"] = seat_status_map.get(seat.id, 'dead')
            else:
                seat_data["status"] = 'dead'
        
        matrix_dict[seat.row].append(seat_data)

    # 行番号順に並べ替えて2次元配列を生成
    sorted_rows = sorted(matrix_dict.keys())
    seat_matrix = [matrix_dict[r] for r in sorted_rows]

    context = {
        'seat_matrix': seat_matrix,
    }
    return render(request, 'seat_map.html', context)
```

### 3. ルーティング設定 (`urls.py`)
- **アプリケーション個別URL**: [alive_check/urls.py](file:///home/ubuntu/Develop/Django-Ping/alive_check/urls.py)
  ```python
  from django.urls import path
  from .views import seat_map_view

  urlpatterns = [
      path('', seat_map_view, name='seat_map'),
  ]
  ```

- **プロジェクト全体ルートURL**: [classroom_ping/urls.py](file:///home/ubuntu/Develop/Django-Ping/classroom_ping/urls.py)
  ```python
  from django.contrib import admin
  from django.urls import path, include

  urlpatterns = [
      path('admin/', admin.site.urls),
      path('', include('alive_check.urls')),  # ルートアクセス時に座席マップを表示
  ]
  ```

### 4. 初期データ投入スクリプト (`seed_data.py`)
- **配置先**: [seed_data.py](file:///home/ubuntu/Develop/Django-Ping/seed_data.py)

動作検証用として、6行×5列（計30スロット）のグリッド（通路と、応答するIP `127.0.0.1` や `8.8.8.8` 、応答しないIP、空のIPなどを組み合わせたデータ）を自動作成します。

---

## 🔍 動作検証手順

システムを起動して正しく動作するか検証する手順です。

### 1. マイグレーションの実行と初期データの作成
以下のコマンドを実行し、データベース構築とデータ投入を行います。

```bash
# 仮想環境を有効化
source .venv/bin/activate

# データベースマイグレーション
python manage.py makemigrations
python manage.py migrate

# テストデータの投入
python seed_data.py
```

### 2. 開発サーバーの起動
以下のコマンドでサーバーを起動します。
```bash
python manage.py runserver 127.0.0.1:8000
```

### 3. ブラウザまたはCurlでの表示テスト
ブラウザで `http://127.0.0.1:8000/` にアクセスするか、以下のコマンドを実行します。
```bash
curl -sS http://127.0.0.1:8000/
```

- 応答可能な `127.0.0.1` などのIPを持つ座席は `alive`（緑色のパルスアニメーション付きインジケータ）として表示されます。
- 無効なIP（`192.0.2.x`）やIP未設定の座席は `dead`（赤色インジケータ）として表示されます。
- 通路はグリッド上の余白として透過表示されます。
