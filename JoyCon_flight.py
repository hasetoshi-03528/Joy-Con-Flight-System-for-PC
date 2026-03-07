# -*- coding: utf-8 -*-
import hid
import time
import sys

# --- ユーザー設定 (感度・ノイズ調整) ---
STICK_DEADZONE = 0.15   # 15%以下を無視
GYRO_DEADZONE = 120     # 静止時の微細な振動をカット (100-150で調整)
ALPHA = 0.08            # さらに低速化 (0.05~0.1: 非常に滑らか)
HYSTERESIS = 15         # 数値がこれ以上変化しない限り、表示を更新しない

# --- キャリブレーションデータ ---
OFFSETS = {
    0x2006: {'x': 3588, 'y': 1762, 'z': 818}, # L
    0x2007: {'x': 826, 'y': 1700, 'z': 800}   # R
}

CALIB = {
    'R': {
        'C': (1891, 1782), 'U': 2031, 'D': 664, 'L': 966, 'R': 3157,
        'map': {
            'X': (3, 0x02), 'Y': (3, 0x01), 'A': (3, 0x08), 'B': (3, 0x04),
            'plus': (4, 0x02), 'home': (4, 0x10), 'R': (3, 0x40), 'ZR': (3, 0x80),
            'R1': (3, 0x10), 'R2': (3, 0x20), 'R3': (4, 0x04)
        }
    },
    'L': {
        'C': (2058, 2121), 'U': 3164, 'D': 2103, 'L': 900, 'R': 2940,
        'map': {
            'up': (5, 0x02), 'down': (5, 0x01), 'left': (5, 0x08), 'right': (5, 0x04),
            'minus': (4, 0x01), 'L': (5, 0x40), 'ZL': (5, 0x80),
            'L1': (5, 0x20), 'L2': (5, 0x10), 'L3': (4, 0x08), 'capture': (4, 0x20)
        }
    }
}

def apply_deadzone(value, threshold):
    if abs(value) < threshold: return 0.0
    sign = 1 if value > 0 else -1
    return round(sign * (abs(value) - threshold) / (1.0 - threshold), 2)

def normalize_stick(raw_h, raw_v, side):
    c = CALIB[side]
    h = (raw_h - c['C'][0]) / (c['R'] - c['C'][0]) if raw_h >= c['C'][0] else (raw_h - c['C'][0]) / (c['C'][0] - c['L'])
    v = (raw_v - c['C'][1]) / (c['U'] - c['C'][1]) if raw_v >= c['C'][1] else (raw_v - c['C'][1]) / (c['C'][1] - c['D'])
    return apply_deadzone(h, STICK_DEADZONE), apply_deadzone(v, STICK_DEADZONE)

def get_buttons(report, side):
    pressed = [name for name, (pos, bit) in CALIB[side]['map'].items() if report[pos] & bit]
    return "/".join(pressed) if pressed else "---"

def main():
    # 内部状態保持
    con_states = {
        'L': {'b': "", 's': (0.0, 0.0), 'g_filt': [0.0, 0.0], 'dg': [0, 0]}, 
        'R': {'b': "", 's': (0.0, 0.0), 'g_filt': [0.0, 0.0], 'dg': [0, 0]}
    }
    
    devices = []
    for info in hid.enumerate(0x057e):
        pid = info['product_id']
        if pid in [0x2006, 0x2007]:
            d = hid.device()
            d.open_path(info['path'])
            d.set_nonblocking(True)
            d.write(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x40\x01')
            d.write(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x30')
            devices.append({'dev': d, 'side': "L" if pid == 0x2006 else "R", 'pid': pid})

    if not devices:
        print("Joy-Conが見つかりません。")
        return

    print(f"=== Joy-Con Flight Ultra (LPF:{ALPHA}, HYST:{HYSTERESIS}) ===")
    
    try:
        while True:
            for dev in devices:
                report = dev['dev'].read(64)
                if report and len(report) >= 25:
                    side = dev['side']
                    st = con_states[side]
                    
                    # 1. スティック
                    s_idx = 6 if side == "L" else 9
                    raw_h = report[s_idx] | ((report[s_idx+1] & 0x0F) << 8)
                    raw_v = (report[s_idx+1] >> 4) | (report[s_idx+2] << 4)
                    st['s'] = normalize_stick(raw_h, raw_v, side)
                    
                    # 2. ボタン
                    st['b'] = get_buttons(report, side)
                    
                    # 3. ジャイロ
                    gx_raw = int.from_bytes(bytes(report[19:21]), 'little', signed=True) - OFFSETS[dev['pid']]['x']
                    gz_raw = int.from_bytes(bytes(report[23:25]), 'little', signed=True) - OFFSETS[dev['pid']]['z']
                    
                    # 強力なデッドゾーン
                    gx_in = gx_raw if abs(gx_raw) > GYRO_DEADZONE else 0
                    gz_in = gz_raw if abs(gz_raw) > GYRO_DEADZONE else 0
                    
                    # 低域通過フィルタ (LPF)
                    st['g_filt'][0] = st['g_filt'][0] * (1 - ALPHA) + gx_in * ALPHA
                    st['g_filt'][1] = st['g_filt'][1] * (1 - ALPHA) + gz_in * ALPHA
                    
                    # ヒステリシス (遊び) 処理: 前回の表示値と大きく変わらない限り更新しない
                    new_gx = int(round(st['g_filt'][0]))
                    new_gz = int(round(st['g_filt'][1]))
                    
                    if abs(new_gx - st['dg'][0]) > HYSTERESIS or gx_in == 0:
                        st['dg'][0] = new_gx if gx_in != 0 else 0
                    if abs(new_gz - st['dg'][1]) > HYSTERESIS or gz_in == 0:
                        st['dg'][1] = new_gz if gz_in != 0 else 0

            # 出力
            out = (f"\rL:[B:{con_states['L']['b']:12} S:{con_states['L']['s']} G:{con_states['L']['dg'][0]:5},{con_states['L']['dg'][1]:5}] | "
                   f"R:[B:{con_states['R']['b']:12} S:{con_states['R']['s']} G:{con_states['R']['dg'][0]:5},{con_states['R']['dg'][1]:5}]")
            sys.stdout.write(out + " " * 5)
            sys.stdout.flush()
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nFinished.")
    finally:
        for d in devices:
            d['dev'].close()

if __name__ == "__main__":
    main()