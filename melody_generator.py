# melody_generator.py
import random
from mido import Message, MidiFile, MidiTrack

# 🎯 音階設定範圍：C4 (60) 到 C5 (72)
LOWER = 60
UPPER = 72

# 🎛 音程機率分佈
INTERVAL_PROBS = {
    0: 0.2,   # 同音重複
    1: 0.4,   # 步進：1度
    2: 0.25,  # 小跳：2度（小三度或大三度可以映射）
    3: 0.1,   # 中距離跳進（4度）
    4: 0.05   # 大跳進（≥5度，少用）
}

# 🎚 動向上下控制機率分佈
TREND_PROBS = {
    "up": 0.6,
    "down": 0.3,
    "static": 0.1
}

def choose_interval():
    """依 INTERVAL_PROBS 機率選擇音程大小。"""
    r = random.random()
    acc = 0
    for interval, p in INTERVAL_PROBS.items():
        acc += p
        if r < acc:
            return interval
    return 0

def choose_trend():
    """決定本次旋律移動趨勢：上、下或靜止。"""
    r = random.random()
    acc = 0
    for t, p in TREND_PROBS.items():
        acc += p
        if r < acc:
            return t
    return "static"

def apply_jump_rules(curr, interval, direction):
    """
    根據當前音，選擇移動的方向 (+1 up / -1 down)，
    並確保音域範圍 LOWER–UPPER 內。
    """
    assert direction in ("up", "down", "static")
    if direction == "static": return curr

    # 隨機選擇方向或固定方向
    delta = interval if direction == "up" else -interval

    # 避免超出界線
    next_note = curr + delta
    if next_note < LOWER or next_note > UPPER:
        next_note = curr - delta  # 反方向反彈
        if next_note < LOWER or next_note > UPPER:
            next_note = curr  # 無法跳動則靜止
    return next_note

def generate_melody(length=16):
    """
    主函式：根據音程與動向規則生成旋律。
    參數 length：旋律長度（音符數）。
    """
    melody = []
    curr = random.randint(LOWER, UPPER)
    for i in range(length):
        trend = choose_trend()         # 決定上升/下降/靜止
        interval = choose_interval()   # 選擇跳多少音級
        next_note = apply_jump_rules(curr, interval, trend)
        melody.append(next_note)
        curr = next_note
    return melody

def save_midi(melody, filename="output.mid", tick=480):
    """將音高序列輸出為 MIDI 檔。"""
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)
    time = tick  # 每音符固定时值

    for note in melody:
        track.append(Message('note_on', note=note, velocity=64, time=0))
        track.append(Message('note_off', note=note, velocity=64, time=time))

    mid.save(filename)
    print(f"✅ 已儲存：{filename}")

if __name__ == "__main__":
    mel = generate_melody(32)  # 生成 32 個音符的旋律
    print("生成功能旋律（MIDI 音高）:", mel)
    save_midi(mel, "generated.mid")
