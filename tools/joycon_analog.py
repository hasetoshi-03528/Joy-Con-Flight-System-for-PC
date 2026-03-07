# -*- coding: utf-8 -*-
import hid
import time

VENDOR_ID = 0x057e
PIDS = {"L": 0x2006, "R": 0x2007}

def get_joycons():
    devices = []
    for info in hid.enumerate(VENDOR_ID):
        if info['product_id'] in PIDS.values():
            d = hid.device()
            d.open_path(info['path'])
            d.set_nonblocking(True)
            d.write(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x30')
            side = "L" if info['product_id'] == 0x2006 else "R"
            devices.append({'dev': d, 'side': side})
    return devices

def parse_stick(report, side):
    """詳細レポート(0x30)からスティックの12bit値を抽出"""
    if side == "L":
        # Byte 6, 7, 8 が左スティック
        data = report[6:9]
        x = data[0] | ((data[1] & 0x0F) << 8)
        y = (data[1] >> 4) | (data[2] << 4)
    else:
        # Byte 9, 10, 11 が右スティック
        data = report[9:12]
        x = data[0] | ((data[1] & 0x0F) << 8)
        y = (data[1] >> 4) | (data[2] << 4)
    return x, y

def main():
    devices = get_joycons()
    if not devices:
        print("Joy-Conが見つかりません。")
        return

    all_results = {}

    for device in devices:
        side = device['side']
        print(f"\n=== Joy-Con ({side}) スティック記録開始 ===")
        results = {}
        
        # 記録するポジションのリスト
        positions = ["Center", "Up", "Down", "Left", "Right"]
        
        for pos in positions:
            input(f"[{side}] スティックを『{pos}』に保ち、Enterを押してください...")
            
            # 数回読み取って平均に近い値をとる
            samples_x = []
            samples_y = []
            for _ in range(20):
                report = device['dev'].read(64)
                if report and len(report) >= 12:
                    x, y = parse_stick(report, side)
                    samples_x.append(x)
                    samples_y.append(y)
                time.sleep(0.01)
            
            if samples_x:
                avg_x = sum(samples_x) // len(samples_x)
                avg_y = sum(samples_y) // len(samples_y)
                results[pos] = (avg_x, avg_y)
                print(f"  => 記録完了: X={avg_x}, Y={avg_y}")
            else:
                print("  => データ読み取り失敗。")

        all_results[side] = results
        device['dev'].close()

    print("\n" + "="*40)
    print("--- 最終スティック記録結果 ---")
    print("="*40)
    for side, res in all_results.items():
        print(f"\nSTICK_DATA_{side} = {{")
        for pos, val in res.items():
            print(f"    '{pos}': {val},")
        print("}")

if __name__ == "__main__":
    main()