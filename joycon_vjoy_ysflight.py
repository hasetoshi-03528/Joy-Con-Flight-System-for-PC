# -*- coding: utf-8 -*-
import hid, time, sys, pyvjoy, math, threading
from pynput.keyboard import Key, Controller

# --- ユーザー設定 ---
STICK_DEADZONE = 0.22 
GYRO_SENSE = 50.0  
keyboard = Controller()

BASE_ACCEL = {
    0x2006: {'x': 3477, 'y': 1954, 'z': 859}, 
    0x2007: {'x': 3702, 'y': 1779, 'z': 19}   
}

CALIB = {
    'R': {
        'C': (2020, 1753), 'U': 2814, 'D': 753, 'L': 870, 'R': 3102,
        'map': {
            'A': (3, 0x08), 'B': (3, 0x04), 'X': (3, 0x02), 'Y': (3, 0x01),
            'R1': (3, 0x10), 'R2': (3, 0x20), 'R': (3, 0x40), 'ZR': (3, 0x80),
            'plus': (4, 0x02), 'R3': (4, 0x04),
            'A_s': (1, 0x01), 'B_s': (1, 0x02), 'X_s': (1, 0x04), 'Y_s': (1, 0x08),
            'R1_s': (2, 0x01), 'R2_s': (2, 0x02), 'plus_s': (2, 0x10)
        }
    },
    'L': {
        'C': (2027, 2141), 'U': 3117, 'D': 1106, 'L': 894, 'R': 3225,
        'map': {
            'L1': (5, 0x20), 'L2': (5, 0x10), 'L': (5, 0x40), 'ZL': (5, 0x80),
            'minus': (4, 0x01), 'L3': (4, 0x08),
            'L1_s': (2, 0x01), 'L2_s': (2, 0x02), 'minus_s': (2, 0x10)
        }
    }
}

KEY_HOLD_MAP = {'A': ' ', 'plus': 'q', 'minus': 'a', 'R2': Key.tab, 'ZL': 'b', 'L1': 'z', 'L2': 'c'}
KEY_PRESS_MAP = {'B': '2', 'X': '3', 'Y': '4', 'ZR': 'g', 'L': 'f', 'R': 'r'}

con_states = {'L': {'b': [], 'dg': [0, 0], 's': (0.0, 0.0), 'acc': (0,0,0), 'batt': 0}, 
              'R': {'b': [], 'dg': [0, 0], 's': (0.0, 0.0), 'acc': (0,0,0), 'batt': 0}}
key_active_states = {}
running = True

def get_key_name(k):
    if k == ' ': return 'space'
    if k == Key.tab: return 'tab'
    return str(k).replace("'", "").upper() if isinstance(k, str) and len(k) == 1 else str(k).replace("'", "")

def normalize_stick(raw_h, raw_v, side):
    c = CALIB[side]
    h = (raw_h - c['C'][0]) / max(1, (c['R'] - c['C'][0])) if raw_h >= c['C'][0] else (raw_h - c['C'][0]) / max(1, (c['C'][0] - c['L']))
    v = (raw_v - c['C'][1]) / max(1, (c['U'] - c['C'][1])) if raw_v >= c['C'][1] else (raw_v - c['C'][1]) / max(1, (c['C'][1] - c['D']))
    return (max(-1.0, min(1.0, h)) if abs(h) > STICK_DEADZONE else 0.0), (max(-1.0, min(1.0, v)) if abs(v) > STICK_DEADZONE else 0.0)

def joycon_thread(devices, j):
    while running:
        for dev in devices:
            try:
                report = dev['dev'].read(64)
                if not report: continue
                side = dev['side']; st = con_states[side]
                if report[0] == 0x30:
                    st['batt'] = {8:100, 6:75, 4:50, 2:25}.get((report[2] & 0xF0) >> 4, 0)
                    st['b'] = [n for n, (pos, bit) in CALIB[side]['map'].items() if len(report) > pos and report[pos] & bit and '_s' not in n]
                    ax, ay, az = [int.from_bytes(bytes(report[i:i+2]), 'little', signed=True) for i in [13, 15, 17]]
                    st['acc'] = (ax, ay, az)
                    base = BASE_ACCEL[dev['pid']]
                    st['dg'][0] = int(max(-2000, min(2000, (math.atan2(az, ax) - math.atan2(base['z'], base['x'])) * (180/math.pi) * GYRO_SENSE)))
                    st['dg'][1] = int(max(-2000, min(2000, (math.atan2(ay, ax) - math.atan2(base['y'], base['x'])) * (180/math.pi) * GYRO_SENSE)))
                    s_idx = 6 if side == "L" else 9
                    rh = report[s_idx] | ((report[s_idx+1] & 0x0F) << 8); rv = (report[s_idx+1] >> 4) | (report[s_idx+2] << 4)
                    st['s'] = normalize_stick(rh, rv, side)
                elif report[0] == 0x3f:
                    st['b'] = [n.replace('_s','') for n, (pos, bit) in CALIB[side]['map'].items() if len(report) > pos and report[pos] & bit and '_s' in n]
            except: continue
        
        j.set_axis(pyvjoy.HID_USAGE_X, int(((-con_states['L']['dg'][0]/2000)+1)*16383.5))
        j.set_axis(pyvjoy.HID_USAGE_Y, int(((-con_states['L']['dg'][1]/2000)+1)*16383.5))
        j.set_button(1, 1 if 'R1' in con_states['R']['b'] else 0)

def main():
    global running
    try: j = pyvjoy.VJoyDevice(1)
    except: return
    devices = []
    for info in hid.enumerate(0x057e):
        pid = info['product_id']
        if pid in [0x2006, 0x2007]:
            d = hid.device(); d.open_path(info['path']); d.set_nonblocking(True)
            d.write(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x40\x01')
            d.write(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x30')
            devices.append({'dev': d, 'side': "L" if pid == 0x2006 else "R", 'pid': pid})

    t = threading.Thread(target=joycon_thread, args=(devices, j), daemon=True)
    t.start()

    print("=== Joy-Con Absolute Control (Fixed Format) ===")
    prev_all_b = []
    try:
        while True:
            L, R = con_states['L'], con_states['R']
            current_all_b = L['b'] + R['b']
            
            target_keys = {}
            for jb, kv in KEY_HOLD_MAP.items(): 
                if jb in current_all_b: target_keys[kv] = True
            
            # --- 修正：スティック上がU、下がJ ---
            rv_map = {'u': R['s'][1] > 0.5, 'j': R['s'][1] < -0.5, 'k': R['s'][0] > 0.5, 'h': R['s'][0] < -0.5}
            for k, prs in rv_map.items():
                if prs: target_keys[k] = True

            all_holdable = list(KEY_HOLD_MAP.values()) + ['u', 'j', 'k', 'h']
            for k in all_holdable:
                should_press = target_keys.get(k, False)
                if should_press and not key_active_states.get(k, False):
                    keyboard.press(k); key_active_states[k] = True
                elif not should_press and key_active_states.get(k, False):
                    keyboard.release(k); key_active_states[k] = False
            for jb, kv in KEY_PRESS_MAP.items():
                if jb in current_all_b and jb not in prev_all_b:
                    keyboard.press(kv); keyboard.release(kv)

            v_btns = ["1"] if 'R1' in R['b'] else []
            btn_map_disp = {2:'B', 3:'X', 4:'Y', 5:'ZR', 6:'L', 7:'ZL', 8:'R', 10:'plus', 11:'minus', 12:'R2', 13:'L1', 14:'L2', 1:'A'}
            for b_num, name in btn_map_disp.items():
                if name in current_all_b: v_btns.append(str(b_num))
            if 'R3' in current_all_b: v_btns.append("R3")
            
            active_names = [get_key_name(k) for k, v in key_active_states.items() if v]
            for jb, kv in KEY_PRESS_MAP.items():
                if jb in current_all_b: active_names.append(get_key_name(kv))

            sys.stdout.write(f"\rJoyCon（L）電池残量：{L['batt']:03d}％｜JoyCon（R）電池残量：{R['batt']:03d}％\n")
            sys.stdout.write(f"[L] G[R:{L['dg'][0]:+05d},P:{L['dg'][1]:+05d}]({L['acc'][0]:+05d},{L['acc'][1]:+05d},{L['acc'][2]:+05d}) S:{L['s'][0]:+0.2f},{L['s'][1]:+0.2f} B:{''.join(L['b']):7.7s}| "
                             f"[R] G[R:{R['dg'][0]:+05d},P:{R['dg'][1]:+05d}]({R['acc'][0]:+05d},{R['acc'][1]:+05d},{R['acc'][2]:+05d}) S:{R['s'][0]:+0.2f},{R['s'][1]:+0.2f} B:{''.join(R['b']):7.7s}| B_vJoy: {' '.join(v_btns):10s} KBD: {' '.join(list(set(active_names))):10s}\033[F")
            sys.stdout.flush()
            
            prev_all_b = current_all_b[:]
            time.sleep(0.005)
    except KeyboardInterrupt:
        running = False
        print("\n\nFinnish!!!")
    finally:
        [d['dev'].close() for d in devices]

if __name__ == "__main__": main()