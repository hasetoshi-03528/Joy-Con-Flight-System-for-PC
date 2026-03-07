# -*- coding: utf-8 -*-
import hid
import time
import sys
import pyvjoy

# --- ユーザー設定 ---
STICK_DEADZONE = 0.15
GYRO_DEADZONE = 100
ALPHA = 0.10
HYSTERESIS = 12
YAW_SPEED = 0.05 

# --- キャリブレーションデータ ---
OFFSETS = {
    0x2007: {'x': 15, 'y': 0, 'z': 11},  # Right
    0x2006: {'x': 30, 'y': 0, 'z': 1}    # Left
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
    return [name for name, (pos, bit) in CALIB[side]['map'].items() if report[pos] & bit]

def to_vjoy(val, limit=2000):
    if isinstance(val, float):
        norm = max(-1.0, min(1.0, val))
    else:
        norm = max(-1.0, min(1.0, val / limit))
    return int((norm + 1.0) * 16383.5)

def main():
    try:
        j = pyvjoy.VJoyDevice(1)
    except Exception as e:
        print(f"vJoy初期化失敗: {e}"); return

    con_states = {
        'L': {'b': [], 's': (0.0, 0.0), 'g_filt': [0.0, 0.0], 'dg': [0, 0]}, 
        'R': {'b': [], 's': (0.0, 0.0), 'g_filt': [0.0, 0.0], 'dg': [0, 0]}
    }
    
    current_yaw = 0.0
    devices = []
    
    for info in hid.enumerate(0x057e):
        pid = info['product_id']
        if pid in [0x2006, 0x2007]:
            d = hid.device(); d.open_path(info['path']); d.set_nonblocking(True)
            d.write(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x40\x01')
            d.write(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x30')
            devices.append({'dev': d, 'side': "L" if pid == 0x2006 else "R", 'pid': pid})

    print("=== Joy-Con Full Monitor (L/R All Data) ===")
    
    try:
        while True:
            for dev in devices:
                report = dev['dev'].read(64)
                if report and len(report) >= 25:
                    side = dev['side']; st = con_states[side]
                    # スティック生値の抽出
                    s_idx = 6 if side == "L" else 9
                    raw_h = report[s_idx] | ((report[s_idx+1] & 0x0F) << 8)
                    raw_v = (report[s_idx+1] >> 4) | (report[s_idx+2] << 4)
                    
                    st['s'] = normalize_stick(raw_h, raw_v, side)
                    st['b'] = get_buttons(report, side)
                    
                    # ジャイロ生値の抽出
                    gx_raw = int.from_bytes(bytes(report[19:21]), 'little', signed=True) - OFFSETS[dev['pid']]['x']
                    gz_raw = int.from_bytes(bytes(report[23:25]), 'little', signed=True) - OFFSETS[dev['pid']]['z']
                    gx_in = gx_raw if abs(gx_raw) > GYRO_DEADZONE else 0
                    gz_in = gz_raw if abs(gz_raw) > GYRO_DEADZONE else 0
                    
                    st['g_filt'][0] = st['g_filt'][0] * (1 - ALPHA) + gx_in * ALPHA
                    st['g_filt'][1] = st['g_filt'][1] * (1 - ALPHA) + gz_in * ALPHA
                    
                    new_gx = int(round(st['g_filt'][0]))
                    new_gz = int(round(st['g_filt'][1]))
                    if abs(new_gx - st['dg'][0]) > HYSTERESIS or gx_in == 0: st['dg'][0] = new_gx if gx_in != 0 else 0
                    if abs(new_gz - st['dg'][1]) > HYSTERESIS or gz_in == 0: st['dg'][1] = new_gz if gz_in != 0 else 0

            # ヨーのスムージング
            target_yaw = 0.0
            if 'L2' in con_states['L']['b']: target_yaw += 1.0
            if 'L1' in con_states['L']['b']: target_yaw -= 1.0
            if current_yaw < target_yaw: current_yaw = min(target_yaw, current_yaw + YAW_SPEED)
            elif current_yaw > target_yaw: current_yaw = max(target_yaw, current_yaw - YAW_SPEED)

            # vJoy 出力
            j.set_axis(pyvjoy.HID_USAGE_RX, to_vjoy(con_states['R']['dg'][0]))
            j.set_axis(pyvjoy.HID_USAGE_RY, to_vjoy(con_states['R']['dg'][1]))
            j.set_axis(pyvjoy.HID_USAGE_X, to_vjoy(con_states['L']['dg'][0])) 
            j.set_axis(pyvjoy.HID_USAGE_Y, to_vjoy(-con_states['L']['dg'][1])) 
            j.set_axis(pyvjoy.HID_USAGE_RZ, to_vjoy(current_yaw))
            j.set_axis(pyvjoy.HID_USAGE_Z, to_vjoy(con_states['L']['s'][1]))

            # --- 全データ固定長出力 ---
            l_gyro = f"G:{con_states['L']['dg'][0]:+05d},{con_states['L']['dg'][1]:+05d}"
            r_gyro = f"G:{con_states['R']['dg'][0]:+05d},{con_states['R']['dg'][1]:+05d}"
            l_stick = f"S:{con_states['L']['s'][0]:+1.2f},{con_states['L']['s'][1]:+1.2f}"
            r_stick = f"S:{con_states['R']['s'][0]:+1.2f},{con_states['R']['s'][1]:+1.2f}"
            l_btns = ",".join(con_states['L']['b'])[:10]
            r_btns = ",".join(con_states['R']['b'])[:10]
            
            # コンソール一行出力 (幅を固定してチラつきを防止)
            sys.stdout.write(
                f"\r[L] {l_gyro} {l_stick} B:{l_btns:10} | "
                f"[R] {r_gyro} {r_stick} B:{r_btns:10} | "
                f"Y:{current_yaw:+.2f} "
            )
            sys.stdout.flush()
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nFinished.")
    finally:
        for d in devices: d['dev'].close()

if __name__ == "__main__":
    main()