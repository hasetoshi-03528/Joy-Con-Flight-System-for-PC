# -*- coding: utf-8 -*-
import hid
import time
import sys

def get_gyro_calibration():
    devices = []
    # 接続されているJoy-Conをスキャン
    for info in hid.enumerate(0x057e):
        pid = info['product_id']
        if pid in [0x2006, 0x2007]:
            d = hid.device()
            d.open_path(info['path'])
            d.set_nonblocking(True)
            # IMUを有効化し、詳細レポートモード(0x30)へ設定
            d.write(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x40\x01')
            d.write(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x30')
            side = "L" if pid == 0x2006 else "R"
            devices.append({'dev': d, 'side': side, 'pid': pid})
    
    if not devices:
        print("Joy-Conが見つかりません。USB接続またはBluetoothペアリングを確認してください。")
        return

    print("\n" + "="*60)
    print("      Joy-Con フライト用基準値（オフセット）自動測定")
    print("="*60)
    print("1. Joy-Conを【操縦桿を握る姿勢（トリガーが上）】で持ちます。")
    print("2. 測定中、デスクに置くか両手で支えて【完全に静止】させてください。")
    print("-" * 60)

    # 10秒カウントダウン（15秒は長すぎるため、集中力が切れない10秒に最適化）
    for i in range(10, 0, -1):
        sys.stdout.write(f"\r測定開始まであと {i:2} 秒... 静止してください！")
        sys.stdout.flush()
        time.sleep(1)
    
    print("\n\n>>> 記録中（約2秒間）... そのまま動かないでください...")

    final_offsets = {}
    for device in devices:
        gx_list, gz_list = [], []
        # 200サンプル取得して精度を高める
        samples = 0
        while samples < 200:
            report = device['dev'].read(64)
            # 操縦システムと同じインデックス(19-25)からジャイロ値を抽出
            if report and len(report) >= 25:
                gx = int.from_bytes(bytes(report[19:21]), 'little', signed=True)
                gz = int.from_bytes(bytes(report[23:25]), 'little', signed=True)
                gx_list.append(gx)
                gz_list.append(gz)
                samples += 1
            time.sleep(0.01)
        
        # 平均値を算出
        final_offsets[device['side']] = {
            'x': sum(gx_list) // len(gx_list),
            'z': sum(gz_list) // len(gz_list)
        }
        print(f"  => {device['side']} ({'Left' if device['side']=='L' else 'Right'}) 完了")
        device['dev'].close()

    print("\n" + "#"*50)
    print("### 以下の数値をコピーして教えてください ###")
    print("#"*50)
    print("OFFSETS = {")
    for i, (side, off) in enumerate(final_offsets.items()):
        pid_hex = "0x2006" if side == "L" else "0x2007"
        comma = "," if i < len(final_offsets)-1 else ""
        print(f"    {pid_hex}: {{'x': {off['x']}, 'y': 0, 'z': {off['z']}}}{comma}")
    print("}")
    print("#"*50)

if __name__ == "__main__":
    get_gyro_calibration()