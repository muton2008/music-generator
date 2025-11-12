# main.py
import threading
import time
from typing import List
from generator import MelodicGenerator
from player import play_phrase_from_grid

# ====== 全局播放列表 ======
play_queue: List[List[int]] = []

# ====== 生成線程 ======
def generator_thread(scale_notes, total_steps=128, steps_per_bar=16, trend_strength=0.4, rest_prob=0.05, chord_change_every=16):
    mg = MelodicGenerator(
        scale_notes=scale_notes,
        total_steps=total_steps,
        steps_per_bar=steps_per_bar,
        trend_strength=trend_strength,
        rest_prob=rest_prob,
        chord_change_every=chord_change_every
    )
    while True:
        # 保證至少有3個樂句
        if len(play_queue) < 3:
            phrase = mg.generate_phrase(show_plot=False)
            play_queue.append(phrase)
            print(f"Generated phrase, queue length: {len(play_queue)}")
        time.sleep(0.1)  # 避免占用 CPU 過高

# ====== 播放線程 ======
def player_thread(step_duration=0.375):
    print("Player will start in 3 seconds...")
    time.sleep(3)
    while True:
        if play_queue:
            phrase = play_queue.pop(0)
            print(f"Playing phrase, queue length: {len(play_queue)}")
            play_phrase_from_grid(phrase, step_duration=step_duration)
        else:
            time.sleep(0.1)  # 等待有新樂句

# ====== 測試 ======
if __name__ == "__main__":
    # C大調音階
    C_major_scale = [60, 62, 64, 65, 67, 69, 71, 72]

    # 建立線程
    t_gen = threading.Thread(target=generator_thread, args=(C_major_scale,), daemon=True)
    t_play = threading.Thread(target=player_thread, args=(0.27,), daemon=True)

    t_gen.start()
    t_play.start()

    # 主線程保持運行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
