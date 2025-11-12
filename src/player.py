# piano_player.py
import pygame.midi
import time
from typing import List

pygame.midi.init()
player = pygame.midi.Output(pygame.midi.get_default_output_id())
player.set_instrument(0)  # Acoustic Grand Piano

# ====== 延音踏板 ======
def pedal_on():
    player.write_short(0xB0, 64, 127)  # 踩下延音踏板

def pedal_off():
    player.write_short(0xB0, 64, 0)    # 放開延音踏板

# ====== 播放函數 ======
def play_phrase_from_grid(grid: List[int], step_duration: float = 0.125):
    """
    grid: 音高列表，-1 表示休止符
    step_duration: 每個 step 的時間 (秒)
    """
    i = 0
    n = len(grid)
    pedal_on()  # 開始時踩踏板

    while i < n:
        note = grid[i]

        if note == -1:
            # 遇到休止符，放開踏板再重新踩
            pedal_off()
            time.sleep(step_duration)
            pedal_on()
            i += 1
            continue

        # 計算連續同音高長度
        dur = step_duration
        j = i + 1
        while j < n and grid[j] == note:
            dur += step_duration
            j += 1

        # 播放音符
        player.note_on(note, 100)
        time.sleep(dur)
        player.note_off(note, 100)

        i = j

    #pedal_off()  # 結束時放開踏板

# ====== 測試 ======
if __name__ == "__main__":
    # 測試音高列表（-1 代表休止）
    test_grid = [60, 60, 62, 62, 64, -1, 64, 65, 65, 67, 67, 67, -1, 69, 69, 71]
    play_phrase_from_grid(test_grid, step_duration=0.375)

    player.close()
    pygame.midi.quit()
