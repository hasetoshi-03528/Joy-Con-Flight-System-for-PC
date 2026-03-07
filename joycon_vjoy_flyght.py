# -*- coding: utf-8 -*-
import hid
import time
import sys
import pyvjoy
import math

# --- ユーザー設定 ---
STICK_DEADZONE = 0.22  # 誤差0.20を考慮して調整
ANGLE_DEADZONE = 150 
YAW_SPEED = 0.05 
JUMP_THRESHOLD = 1500 
GYRO_SENSE = 50.0  # 40度で最大(2000)に設定

# --- 数値は不変 ---
BASE_ACCEL = {
    0x2006: {'x': 3477, 'y': 1954, 'z': 859}, 
    0x2007: {'x': 3702, 'y': 1779, 'z': 19}   
}

CALIB = {
    'R': {
        'C': (2020, 1753), 'U': 2814, 'D': 753, 'L': 870, 'R': 3102,
        'map': {
            'X': (3, 0x02), 'Y': (3, 0x01), 'A': (3, 0x08), 'B': (3, 0x04),
            'plus': (4, 0x02), 'home': (4, 0x10), 'R': (3, 0x40), 'ZR': (3, 0x80),
            'R1': (3, 0x10), 'R2': (3, 0x20), 'R3': (4, 0x04)
        }
    },
    'L': {
        'C': (2027, 2141), 'U': 3117, 'D': 1106, 'L': 894, 'R': 3225,
        'map': {
            'up': (5, 0x02), 'down': (5, 0x01), 'left': (5, 0x08), 'right': (5, 0x04),
            'minus': (4, 0x01), 'L': (5, 0x40), 'ZL': (5, 0x80),
            'L1': (5, 0x20), 'L2': (5, 0x10), 'L3': (4, 0x08), 'capture': (4, 0x20)
        }
    }
}

def get_battery_percentage(report):
    """レポートの2バイト目から電池残量を判定"""
    # 上位4ビットを取得 (0x0, 0x2, 0x4, 0x6, 0x8 のいずれかが一般的)
    batt_raw = (report[2] & 0xF0) >> 4
    # 段階評価を%に変換
    if batt_raw >= 8: return 100
    if batt_raw >= 6: return 75
    if batt_raw >= 4: return 50
    if batt_raw >= 2: return 25
    return 0

def apply_deadzone(value, threshold):
    if abs(value) <= threshold: return 0.0
    sign = 1 if value > 0 else -1
    norm_val = (abs(value) - threshold) / max(0.01, (1.0 - threshold))
    final_val = max(0.0, min(1.0, norm_val))
    return round(sign * final_val, 2)

def apply_angle_deadzone(value, threshold):
    if abs(value) < threshold: return 0
    return value

def normalize_stick(raw_h, raw_v, side):
    c = CALIB[side]
    h = (raw_h - c['C'][0]) / max(1, (c['R'] - c['C'][0])) if raw_h >= c['C'][0] else (raw_h - c['C'][0]) / max(1, (c['C'][0] - c['L']))
    v = (raw_v - c['C'][1]) / max(1, (c['U'] - c['C'][1])) if raw_v >= c['C'][1] else (raw_v - c['C'][1]) / max(1, (c['C'][1] - c['D']))
    h, v = max(-1.0, min(1.0, h)), max(-1.0, min(1.0, v))
    return apply_deadzone(h, STICK_DEADZONE), apply_deadzone(v, STICK_DEADZONE)

def get_buttons(report, side):
    return [name for name, (pos, bit) in CALIB[side]['map'].items() if report[pos] & bit]

def to_vjoy(val, limit=2000):
    norm = max(-1.0, min(1.0, val / limit))
    return int((norm + 1.0) * 16383.5)

def main():
    try:
        j = pyvjoy.VJoyDevice(1)
    except Exception as e:
        print(f"vJoy初期化失敗: {e}"); return

    con_states = {
        'L': {'b': [], 's': (0.0, 0.0), 'dg': [0, 0], 'gyro_raw': (0, 0, 0), 'batt': 0}, 
        'R': {'b': [], 's': (0.0, 0.0), 'dg': [0, 0], 'gyro_raw': (0, 0, 0), 'batt': 0}
    }
    
    current_yaw = 0.0
    devices = []
    current_base = {0x2006: BASE_ACCEL[0x2006].copy(), 0x2007: BASE_ACCEL[0x2007].copy()}
    
    for info in hid.enumerate(0x057e):
        pid = info['product_id']
        if pid in [0x2006, 0x2007]:
            d = hid.device(); d.open_path(info['path']); d.set_nonblocking(True)
            d.write(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x40\x01')
            d.write(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x30')
            devices.append({'dev': d, 'side': "L" if pid == 0x2006 else "R", 'pid': pid})

    # 初回の電池残量取得
    time.sleep(0.1)
    for dev in devices:
        report = dev['dev'].read(64)
        if report and len(report) >= 3:
            con_states[dev['side']]['batt'] = get_battery_percentage(report)

    # 1行目に電池残量を表示
    sys.stdout.write(f"JoyCon（L）電池残量：{con_states['L']['batt']:03d}％｜JoyCon（R）電池残量：{con_states['R']['batt']:03d}％\n")
    print("=== Joy-Con Absolute Control (Fixed Length Display) ===")
    
    try:
        while True:
            for dev in devices:
                report = dev['dev'].read(64)
                if report and len(report) >= 25:
                    side = dev['side']; st = con_states[side]
                    
                    # 電池残量の更新（頻繁にやる必要はないが、レポートから常に取得可能）
                    st['batt'] = get_battery_percentage(report)
                    
                    s_idx = 6 if side == "L" else 9
                    raw_h = report[s_idx] | ((report[s_idx+1] & 0x0F) << 8)
                    raw_v = (report[s_idx+1] >> 4) | (report[s_idx+2] << 4)
                    st['s'] = normalize_stick(raw_h, raw_v, side)
                    st['b'] = get_buttons(report, side)
                    
                    ax = int.from_bytes(bytes(report[13:15]), 'little', signed=True)
                    ay = int.from_bytes(bytes(report[15:17]), 'little', signed=True)
                    az = int.from_bytes(bytes(report[17:19]), 'little', signed=True)
                    gx = int.from_bytes(bytes(report[19:21]), 'little', signed=True)
                    gy = int.from_bytes(bytes(report[21:23]), 'little', signed=True)
                    gz = int.from_bytes(bytes(report[23:25]), 'little', signed=True)
                    st['gyro_raw'] = (gx, gy, gz)

                    base = current_base[dev['pid']]
                    calc_a = (math.atan2(ay, ax) - math.atan2(base['y'], base['x'])) * (180.0 / math.pi)
                    calc_b = (math.atan2(az, ax) - math.atan2(base['z'], base['x'])) * (180.0 / math.pi)

                    new_roll = int(max(-2000, min(2000, calc_b * GYRO_SENSE)))
                    new_pitch = int(max(-2000, min(2000, calc_a * GYRO_SENSE)))
                    
                    if abs(new_roll - st['dg'][0]) < JUMP_THRESHOLD:
                        st['dg'][0] = apply_angle_deadzone(new_roll, ANGLE_DEADZONE)
                    if abs(new_pitch - st['dg'][1]) < JUMP_THRESHOLD:
                        st['dg'][1] = apply_angle_deadzone(new_pitch, ANGLE_DEADZONE)

            # vJoy出力
            j.set_axis(pyvjoy.HID_USAGE_RX, to_vjoy(-con_states['R']['dg'][0])) 
            j.set_axis(pyvjoy.HID_USAGE_RY, to_vjoy(-con_states['R']['dg'][1])) 
            j.set_axis(pyvjoy.HID_USAGE_X, to_vjoy(-con_states['L']['dg'][0])) 
            j.set_axis(pyvjoy.HID_USAGE_Y, to_vjoy(con_states['L']['dg'][1])) 

            target_yaw = 0.0
            if 'L2' in con_states['L']['b']: target_yaw += 1.0
            if 'L1' in con_states['L']['b']: target_yaw -= 1.0
            if current_yaw < target_yaw: current_yaw = min(target_yaw, current_yaw + YAW_SPEED)
            elif current_yaw > target_yaw: current_yaw = max(target_yaw, current_yaw - YAW_SPEED)
            j.set_axis(pyvjoy.HID_USAGE_RZ, to_vjoy(current_yaw))
            j.set_axis(pyvjoy.HID_USAGE_Z, to_vjoy(con_states['L']['s'][1]))

            # データ表示（2行目を常に上書き更新）
            l_gyro_str = (f"G[R:{con_states['L']['dg'][0]:+05d},P:{con_states['L']['dg'][1]:+05d}]"
                          f"(X:{con_states['L']['gyro_raw'][0]:+5d},Y:{con_states['L']['gyro_raw'][1]:+5d},Z:{con_states['L']['gyro_raw'][2]:+5d})")
            r_gyro_str = (f"G[R:{con_states['R']['dg'][0]:+05d},P:{con_states['R']['dg'][1]:+05d}]"
                          f"(X:{con_states['R']['gyro_raw'][0]:+5d},Y:{con_states['R']['gyro_raw'][1]:+5d},Z:{con_states['R']['gyro_raw'][2]:+5d})")
            l_stick = f"S:{con_states['L']['s'][0]:+06.2f},{con_states['L']['s'][1]:+06.2f}"
            r_stick = f"S:{con_states['R']['s'][0]:+06.2f},{con_states['R']['s'][1]:+06.2f}"
            l_btns = ",".join(con_states['L']['b'])[:6]
            r_btns = ",".join(con_states['R']['b'])[:6]
            
            # 電池残量の表示を反映させるために、1行目に戻って書き直す制御も可能ですが、
            # 今回はリクエスト通り「1行目に電池」「2行目に詳細データ」の構成で、詳細は \r で更新します。
            sys.stdout.write(f"\r[L] {l_gyro_str} {l_stick} B:{l_btns:6} | [R] {r_gyro_str} {r_stick} B:{r_btns:6} | Y:{current_yaw:+.2f} ")
            sys.stdout.flush()
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nFinished.")
    finally:
        for d in devices: d['dev'].close()

if __name__ == "__main__":
    main()