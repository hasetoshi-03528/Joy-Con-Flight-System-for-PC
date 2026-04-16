# Joy-Con Absolute Control for YSFLIGHT
**Architect-Driven AI Implementation of a High-Precision Flight Bridge**

## 1. プロジェクト概要
本プロジェクトは、Nintendo Joy-Conの慣性計測装置（IMU）を活用し、PC用フライトシミュレーター（YSFLIGHT、MSFS2020等）を直感的に操縦するためのブリッジシステムです。

既存のフライトスティックは高価ですが、Joy-Conの高性能なジャイロセンサーを活用することで、安価かつ直感的な操縦を実現します。HIDプロトコルでJoy-Conと直接通信し、vJoy仮想ジョイスティックおよびキーボードエミュレーションを介してゲームに入力を渡す仕組みを一から実装しました。

### 技術スタック
- **Language:** Python 3.10+
- **Protocol:** Bluetooth HID (via `hidapi`)
- **Output:** `pyvjoy` (Virtual Joystick), `pynput` (Keyboard Simulation)
- **Architecture:** Multi-threaded Real-time Processing

---

## 2. 開発プロセスとアーキテクトの意思決定
本システムは、管理者が「論理構造の定義とボトルネックの特定」を行い、AIがその要求に対する「最適化実装」を行うという共同作業によって完成しました。単なるコード生成ではなく、以下の論理的判断に基づきシステムを昇華させています。

### 🛠 管理者による最適化の軌跡（対話ログの要約）
| 課題（AIの初期提案） | 管理者の判断と指示 | 解決策（最終実装） |
| :--- | :--- | :--- |
| **処理ラグ**（逐次処理） | 「まだラグがある」と断じ、I/O待ちの干渉を特定。 | **マルチスレッド化**による受信と描画の完全分離。 |
| **入力バッファ溢れ** | Windowsの入力キュー滞留による遅延を分析。 | **ステート制御（エッジ検出）**による信号送信の最小化。 |
| **YSFlight整合性** | 内部番号の不一致を指摘（TRG 4 1設定等）。 | **R1ボタンをvJoy Button 1**に完全固定。 |
| **視点操作の直感性** | 汎用キー設定の不備を修正指示。 | **Rスティック：上U / 下J** へのマッピング変更。 |
| **トレーサビリティ** | デバッグ用データ（acc/スティック値）の欠落を看破。 | 出力フォーマットを固定化し、全データ同期表示。 |

### コンソール出力仕様

デバッグ効率と操縦中の視認性を最大化するため、独自の高密度モニタリングUIを実装しています。ANSIエスケープシーケンスにより、リアルタイムに数値を上書き更新します。

#### 表示例
```text
JoyCon（L）電池残量：100％｜JoyCon（R）電池残量：075％
[L] G[R:+0120,P:-0045](+3470,+1950,+0860) S:+0.00,+0.00 B:L1    | [R] G[R:+0005,P:+0010](+3700,+1780,+0020) S:+0.10,-0.85 B:R3   | B_vJoy: 1 12 KBD: U SPACE
```

#### データフィールド定義
| フィールド | 例 | 説明 |
| :--- | :--- | :--- |
| **G (Gyro)** | `G[R:+0120,P:-0045]` | ジャイロ補正後のロールとピッチ。機体の姿勢に直接対応します。 |
| **( ) (Acc)** | `(+3470,+1950,+0860)` | 加速度センサーのXYZ生データ。物理的な振動や傾斜の監視に使用します。 |
| **S (Stick)** | `S:+0.10,-0.85` | 正規化されたアナログスティック値（-1.00 ～ +1.00 の範囲）。 |
| **B (Button)** | `B:L1` | 現在Joy-Con上で物理的に押されているボタンの名称。 |
| **B_vJoy** | `B_vJoy: 1 12` | vJoy（仮想ジョイスティック）に送信されている仮想ボタンID。 |
| **KBD** | `KBD: U SPACE` | **ステート制御**ロジックによってWindowsへ送出されているアクティブなキーボード入力。 |

---

## 3. 技術的ハイライト
- **HID直接通信**: `hidapi`により、0x30レポートを用いた高精度なパケットデコード（ビット演算）を実装。
- **低遅延マルチスレッド**: 15ms周期のHIDサンプリングを阻害しないよう、受信スレッドと描画スレッドを非同期で駆動。
- **ジャイロキャリブレーション**: 個体差を吸収するオフセット・スティックキャリブレーション機構。
- **終了シーケンス**: Ctrl+Cによるシグナルハンドリングを実装し、終了時に `Finnish!!!` を表示。

---

## 4. 使用ファイル構成

| ファイル | 役割 |
|---|---|
| `JoyCon_flight.py` | **メインスクリプト**（マルチスレッド・ステート制御版） |
| `joycon_status.py` | ジャイロ・スティック値の確認・オフセット取得ツール |
| `joycon_vjoy_flight.py` | vJoy連携・標準入力変換ロジック |
| `joycon_vjoy_ysflight.py` | YSFlight特化型設定版 |

---

## 5. セットアップと実行

### 前準備
1. [vJoy](https://github.com/shmdn/vJoy/releases) をインストール。
2. Joy-ConをPCにBluetoothペアリング。
3. 依存ライブラリのインストール：
   ```bash
   pip install hidapi pyvjoy pynput
   ```

---

---




# . English Version (Project Overview & Documentation)

# Joy-Con Absolute Control for YSFLIGHT
**Architect-Driven AI Implementation of a High-Precision Flight Bridge**

## 1. Project Overview
This project is a high-precision flight control bridge that utilizes the Inertial Measurement Unit (IMU) of Nintendo Joy-Cons to enable intuitive piloting in flight simulators such as YSFLIGHT and MSFS2020.

While dedicated flight sticks are often expensive, this system leverages the high-performance gyro sensors in Joy-Cons to provide a cost-effective yet professional-grade piloting experience. It communicates directly with Joy-Cons via the HID protocol and bridges inputs to the game through vJoy and low-layer keyboard emulation.

### Technical Stack
- **Language:** Python 3.10+
- **Protocol:** Bluetooth HID (via `hidapi`)
- **Output:** `pyvjoy` (Virtual Joystick), `pynput` (Keyboard Simulation)
- **Architecture:** Multi-threaded Real-time Processing

---

## 2. Development Process & Architect's Decision-Making
This system was developed through a collaborative process where the **Architect (Human)** defined the logic and identified bottlenecks, while the **AI (Execution Engine)** provided optimized implementations. It is not merely AI-generated code, but a system refined through the following logical interventions.

### 🛠 Engineering Milestone (Architect's Log)
| Challenge (Initial AI Proposal) | Architect's Direction | Solution (Final Implementation) |
| :--- | :--- | :--- |
| **Input Lag** (Sequential Processing) | Identified I/O interference and demanded zero-latency performance. | **Multi-threaded architecture** separating HID reception from UI/Output. |
| **Input Buffer Overflow** | Analyzed Windows input queue lag during rapid key sends. | **State Control (Edge Detection)** logic to minimize redundant signal transmission. |
| **YSFlight Integration** | Corrected mapping inconsistencies (e.g., TRG 4 1 settings). | Hard-coded **R1 Button to vJoy Button 1** for seamless firing. |
| **View Control Logic** | Redefined mapping for intuitive spatial awareness. | Optimized **R-Stick to U/J keys** for vertical head tracking. |
| **Traceability** | Demanded full transparency of raw sensor data. | Established the **"Golden Rule" format** for synchronized telemetry. |

### Console Output: The "Golden Rule" Format
To maximize debugging efficiency and in-flight monitoring, the system implements a high-density telemetry UI. It utilizes ANSI escape sequences to overwrite and update values in real-time.

#### Example
```text
JoyCon（L）Battely：100％｜JoyCon（R）Battely：075％
[L] G[R:+0120,P:-0045](+3470,+1950,+0860) S:+0.00,+0.00 B:L1    | [R] G[R:+0005,P:+0010](+3700,+1780,+0020) S:+0.10,-0.85 B:R3   | B_vJoy: 1 12 KBD: U SPACE
```

### Data Field Definitions
| Field | Example | Description |
| :--- | :--- | :--- |
| **G (Gyro)** | `G[R:+0120,P:-0045]` | Roll and Pitch after gyro compensation. Maps directly to aircraft attitude. |
| **( ) (Acc)** | `(+3470,+1950,+0860)` | Raw accelerometer XYZ data. Used for monitoring physical vibration and tilt. |
| **S (Stick)** | `S:+0.10,-0.85` | Normalized analog stick values (ranging from -1.00 to +1.00). |
| **B (Button)** | `B:L1` | Name of the physical button currently pressed on the Joy-Con. |
| **B_vJoy** | `B_vJoy: 1 12` | Virtual button IDs being transmitted to vJoy. |
| **KBD** | `KBD: U SPACE` | Active keyboard inputs being sent to Windows, managed by **State Control** logic. |

---

## 3. Technical Highlights
- **Direct HID Communication**: High-precision packet decoding using 0x30 reports via `hidapi`.
- **Low-Latency Multi-threading**: An asynchronous architecture that ensures 15ms HID sampling cycles remain uninterrupted by UI rendering.
- **Gyro Calibration**: Built-in offset and stick calibration to eliminate hardware-specific drift.
- **Signal Handling**: Implemented clean-up logic on `Ctrl+C` to ensure safe process termination with a `Finnish!!!` notification.

---

## 4. Setup & Execution
1. Install [vJoy](https://github.com/shmdn/vJoy/releases).
2. Pair Joy-Cons via Bluetooth.
3. Install dependencies: `pip install hidapi pyvjoy pynput`
4. Run `joycon_status.py` to get offsets, then update constants in the main script.
5. Execute `JoyCon_flight.py`. Press `Ctrl+C` to terminate safely.
