# -*- coding: utf-8 -*-
import hid
import time

# 記録したオフセット値
GYRO_OFFSET_L = {'x': 3588, 'y': 1762, 'z': 818}
GYRO_OFFSET_R = {'x': 826, 'y': 1700, 'z': 800}

def send_command(device, sub_cmd, data=b''):
    """Joy-Conにサブコマンドを送信するヘルパー関数"""
    # 形式: [レポートID(0x01), パケット番号(0-F), ..., サブコマンドID, データ]
    cmd = b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00' + sub_cmd + data
    device.write(cmd)
    time.sleep(0.02) # 送信後の安定待ち

def main():
    devices = []
    for info in hid.enumerate(0x057e):
        pid = info['product_id']
        if pid in [0x2006, 0x2007]:
            d = hid.device()
            d.open_path(info['path'])
            d.set_nonblocking(True)
            
            # 1. ジャイロ・加速度センサーを有効化 (Subcmd 0x40, Data 0x01)
            send_command(d, b'\x40', b'\x01')
            # 2. レポートモードを 0x30 (標準フルモード) に設定
            send_command(d, b'\x03', b'\x30')
            
            side = "L" if pid == 0x2006 else "R"
            devices.append({'dev': d, 'side': side, 'offset': GYRO_OFFSET_L if side == "L" else GYRO_OFFSET_R})

    if not devices:
        print("Joy-Conが見つかりません。")
        return

    print("--- ログ出力開始 (19バイト目以降を参照) ---")
    start_time = time.time()
    
    try:
        while time.time() - start_time < 10:
            for dev in devices:
                report = dev['dev'].read(64)
                # 0x30レポートは通常 49バイト以上の長さになります
                if report and len(report) >= 25:
                    # ジャイロX(Roll相当)は19-20バイト目、Z(Pitch相当)は23-24バイト目
                    raw_x = int.from_bytes(report[19:21], 'little', signed=True)
                    raw_z = int.from_bytes(report[23:25], 'little', signed=True)
                    
                    roll = raw_x - dev['offset']['x']
                    pitch = raw_z - dev['offset']['z']
                    
                    elapsed = time.time() - start_time
                    print(f"{elapsed:.3f}, {dev['side']}, R:{roll:6}, P:{pitch:6}, (Raw:{raw_x:6}, {raw_z:6})")
            
            time.sleep(0.01) # サンプリングレート調整

    except KeyboardInterrupt:
        pass
    finally:
        for d in devices: d['dev'].close()

if __name__ == "__main__":
    main()