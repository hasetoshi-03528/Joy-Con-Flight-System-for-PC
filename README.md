# Joy-Con Flight System for PC

Nintendo Switch の Joy-Con 2本を使い、ジャイロ操作でフライトシミュレーター（MSFS2020・YSFlight等）を直感的に操縦するための Python システムです。

## なぜ作ったか

既存のフライトスティックは高価で、Joy-Con のジャイロセンサーを活用すれば安価かつ直感的な操縦が実現できると考えて開発しました。HID プロトコルで Joy-Con と直接通信し、vJoy 仮想ジョイスティック経由でゲームに入力を渡す仕組みを一から実装しています。

## 技術的なポイント

- **HID 直接通信**：`hidapi` ライブラリで Joy-Con とBluetooth HID 通信
- **ジャイロキャリブレーション**：個体差を吸収するオフセット・スティックキャリブレーション機構を実装
- **vJoy 仮想デバイス連携**：`pyvjoy` で Windows の仮想ジョイスティックとして認識させ、あらゆるゲームに対応
- **デジタルスムージング**：L1/L2 ボタンによるラダー操作のなめらかな補間処理

## 動作環境

- Windows 10 / 11
- Python 3.x
- Joy-Con（左右各1本）、Bluetooth 接続

## セットアップ
```bash
pip install hidapi pyvjoy
```

1. [vJoy](https://github.com/shmdn/vJoy/releases) をインストール
2. Joy-Con を PC に Bluetooth ペアリング
3. `joycon_status.py` でジャイロオフセット値を取得し、`joycon_vjoy_flyght.py` の `OFFSETS` に反映
4. `joycon_analog.py` でスティックキャリブレーション値を取得し `CALIB` に反映
5. `JoyCon_flight.py` を実行

## 使用ファイル

| ファイル | 役割 |
|---|---|
| `JoyCon_flight.py` | メインスクリプト |
| `joycon_status.py` | ジャイロ・スティック値の確認ツール |
| `joycon_vjoy_flyght.py` | vJoy 連携・入力変換ロジック |
| `joycon_vjoy_ysflight.py` | YSFlight 向け設定版 |
