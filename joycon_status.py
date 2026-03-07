# -*- coding: utf-8 -*-
import hid
import time

VENDOR_ID = 0x057e
PIDS = {"L": 0x2006, "R": 0x2007}

# ユーザーが記録した実機マッピングを反映
BUTTON_MAP_R = {
    'X': (3, 0x02), 'Y': (3, 0x01), 'A': (3, 0x08), 'B': (3, 0x04),
    'plus': (4, 0x02), 'home': (4, 0x10), 'R': (3, 0x40), 'ZR': (3, 0x80),
    'R1': (3, 0x10), 'R2': (3, 0x20), 'R3': (4, 0x04)
}

BUTTON_MAP_L = {
    'up': (5, 0x02), 'down': (5, 0x01), 'left': (5, 0x08), 'right': (5, 0x04),
    'minus': (4, 0x01), 'L': (5, 0x40), 'ZL': (5, 0x80), 'L1': (5, 0x20),
    'L2': (5, 0x10), 'L3': (4, 0x08), 'capture': (4, 0x20)
}

def main():
    devices = []
    # 接続されているJoy-Conをすべて探して初期化
    for info in hid.enumerate(VENDOR_ID):
        pid = info['product_id']
        side = "L" if pid == PIDS["L"] else "R" if pid == PIDS["R"] else None
        if side:
            try:
                d = hid.device()
                d.open_path(info['path'])
                d.set_nonblocking(True)
                # 詳細レポートモードへ切り替え
                d.write(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x30')
                devices.append({
                    'dev': d, 
                    'side': side, 
                    'last_pressed': set()
                })
                print(f"Connected: Joy-Con ({side})")
            except Exception as e:
                print(f"接続失敗 ({side}): {e}")

    if not devices:
        print("Joy-Conが見つかりません。")
        return

    print("\n" + "="*50)
    print("Joy-Con リアルタイム・ステータス監視 (実機最適化済み)")
    print("="*50)
    print("入力を待機中... (Ctrl+C で終了)\n")

    try:
        while True:
            for device in devices:
                report = device['dev'].read(64)
                # ボタン領域 (Byte 3, 4, 5) を含むレポートを確認
                if report and len(report) >= 6:
                    mapping = BUTTON_MAP_L if device['side'] == "L" else BUTTON_MAP_R
                    current_pressed = set()

                    # 実機マッピングに基づき、現在押されているボタンを抽出
                    for name, (byte_idx, mask) in mapping.items():
                        if report[byte_idx] & mask:
                            current_pressed.add(name)

                    # 前回のループと状態が変わった時のみ表示
                    if current_pressed != device['last_pressed']:
                        side_label = f"[{device['side']}]"
                        timestamp = time.strftime("%H:%M:%S")
                        
                        if current_pressed:
                            # 押されているボタンを名前順で並べて表示
                            btns = ", ".join(sorted(list(current_pressed)))
                            print(f"{timestamp} {side_label} 押下中: {btns}")
                        else:
                            # 何も押されていない状態になった時
                            print(f"{timestamp} {side_label} 全ボタン離上")
                        
                        device['last_pressed'] = current_pressed
            
            # CPU負荷軽減
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n\nプログラムを終了します。")
    finally:
        for d in devices:
            d['dev'].close()

if __name__ == "__main__":
    main()