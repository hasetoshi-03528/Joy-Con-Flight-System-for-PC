# Joy-Con Flight System for PC

Nintendo SwitchのJoy-Conを2本使い、ジャイロ操作で直感的にフライトシミュレーター（MSFS2020等）を操作するためのPythonシステムです。

## 特徴
- **ジャイロ操縦**: 左コンを傾けてロール・ピッチを操作。
- **カメラ操作**: 右コンを傾けて自由な視点移動。
- **デジタル・スムージング**: L1/L2ボタンによる滑らかなラダー（ヨー）操作。
- **vJoy連携**: 仮想ジョイスティックとして認識されるため、多くのゲームに対応。

## セットアップ

### 1. 必要なソフト
- [vJoy](https://github.com/shmdn/vJoy/releases) のインストール
- Python 3.x

### 2. ライブラリのインストール
```bash
pip install hidapi pyvjoy
