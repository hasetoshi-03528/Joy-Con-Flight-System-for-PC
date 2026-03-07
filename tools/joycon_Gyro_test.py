# -*- coding: utf-8 -*-
import hid
import time

def force_activate_r():
    # R側 (0x2007) だけを狙い撃ち
    r_dev = None
    for info in hid.enumerate(0x057e):
        if info['product_id'] == 0x2007:
            r_dev = hid.device()
            r_dev.open_path(info['path'])
            r_dev.set_nonblocking(True)
            break
    
    if not r_dev:
        print("Joy-Con (R) が見つかりません。")
        return

    print("Joy-Con (R) を叩き起こしています...")
    
    # 連続して異なる初期化コマンドを送信 (詳細モード0x30 + ジャイロ有効化)
    for _ in range(20):
        # 標準的な詳細モード要求
        r_dev.write(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x30')
        # 加速度・ジャイロセンサーの有効化フラグ (0x01)
        r_dev.write(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x40')
        time.sleep(0.05)

    print("5秒間データをスキャンします...")
    samples = []
    end_time = time.time() + 5
    while time.time() < end_time:
        report = r_dev.read(64)
        if report and len(report) >= 19:
            ax = int.from_bytes(report[13:15], 'little', signed=True)
            if ax != 0: # 0以外のデータが来たら成功
                samples.append(ax)
                print(f"受信中... {len(samples)}/100", end="\r")
        if len(samples) >= 100: break
    
    if samples:
        print(f"\n成功！R側のセンサーが反応しました。平均値: {sum(samples)//len(samples)}")
    else:
        print("\nまだRが反応しません。物理的な再接続が必要です。")
    
    r_dev.close()

force_activate_r()