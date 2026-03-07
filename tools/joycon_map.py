# -*- coding: utf-8 -*-
import hid
import time

VENDOR_ID = 0x057e
PIDS = {"L": 0x2006, "R": 0x2007}

def get_specific_joycon(side_code):
    """指定された側 (L または R) のJoy-Conを探して接続する"""
    target_pid = PIDS[side_code]
    for info in hid.enumerate(VENDOR_ID):
        if info['product_id'] == target_pid:
            try:
                d = hid.device()
                d.open_path(info['path'])
                d.set_nonblocking(True)
                # 詳細レポートモード 0x30 へ切り替え
                d.write(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x30')
                return d
            except Exception as e:
                print(f"接続エラー ({side_code}): {e}")
    return None

def record_side(side_label):
    """指定された側のJoy-Conのボタンを記録するループ"""
    device = get_specific_joycon(side_label)
    if not device:
        print(f"\n[!] Joy-Con ({side_label}) が見つかりません。スキップします。")
        return {}

    print(f"\n=== Joy-Con ({side_label}) の記録を開始します ===")
    print(f"手順: キーボードでボタン名を入力 -> そのボタンを Joy-Con ({side_label}) で押す")
    
    mapping_results = {}
    
    try:
        while True:
            btn_name = input(f"\n[{side_label}] 記録するボタン名 (例: {'ZL' if side_label=='L' else 'ZR'} / 次へ進むには 'q'): ").strip()
            if btn_name.lower() == 'q': 
                break
            
            print(f"『{btn_name}』を長押ししてください...")
            
            found = False
            timeout = time.time() + 5
            while time.time() < timeout:
                report = device.read(64)
                if report and len(report) >= 6:
                    # ボタンデータがある Byte 3, 4, 5 をチェック
                    for b_idx in [3, 4, 5]:
                        val = report[b_idx]
                        if val != 0:
                            for bit in range(8):
                                if (val >> bit) & 1:
                                    mask = 1 << bit
                                    mapping_results[btn_name] = {"byte": b_idx, "mask": hex(mask)}
                                    print(f"  => 記録完了: Byte {b_idx}, Mask {hex(mask)}")
                                    found = True
                                    break
                        if found: break
                if found: break
                time.sleep(0.01)
            
            if not found:
                print("  => タイムアウトまたは検知失敗。")
            else:
                print("ボタンを離してください...")
                while True:
                    r = device.read(64)
                    if not r or (r[3]==0 and r[4]==0 and r[5]==0): break
                    time.sleep(0.01)
    finally:
        device.close()
    
    return mapping_results

def main():
    # 1. まず R を記録
    results_r = record_side("R")
    
    # 2. 次に L を記録
    results_l = record_side("L")

    # 3. 最後にまとめて結果を出力
    print("\n" + "="*40)
    print("--- 最終マッピング結果 ---")
    print("="*40)
    
    print("\nBUTTON_MAP_R = {")
    for name, data in results_r.items():
        print(f"    '{name}': {{'byte': {data['byte']}, 'mask': {data['mask']}}},")
    print("}")

    print("\nBUTTON_MAP_L = {")
    for name, data in results_l.items():
        print(f"    '{name}': {{'byte': {data['byte']}, 'mask': {data['mask']}}},")
    print("}")

if __name__ == "__main__":
    main()