# main.py
import threading
import time
import queue

#from generator import MelodicGenerator
from test import MelodicGenerator  # 使用優化版本
import player

PHRASE_BUFFER_LIMIT = 3
STEP_DURATION = 0.25

melody_queue = queue.Queue()
stop_event = threading.Event()

# ====== 旋律生成器 ======
generator = MelodicGenerator(
    base_note=60,
    total_steps=64,
    trend_strength=0.5,
    rest_prob=0.05,
    chord_change_every=16,
    mode="major",
)

# ====== 生成線程 ======
def generator_thread():
    while not stop_event.is_set():
        if melody_queue.qsize() < PHRASE_BUFFER_LIMIT:
            phrase = generator.generate_phrase(show_plot=False)
            melody_queue.put(phrase)
            print(f"[Generator] Queue長度: {melody_queue.qsize()}")
        else:
            time.sleep(1)

# ====== 播放線程 ======
def player_thread():
    print("[Player] 等待3秒開始播放...")
    time.sleep(3)

    while not stop_event.is_set():
        if melody_queue.empty():
            print("[Player] 等待生成樂句中...")
            time.sleep(1)
            continue

        phrase = melody_queue.get()
        print(f"[Player] 播放樂句 (queue剩餘 {melody_queue.qsize()})")
        player.play_phrase_from_grid(phrase, step_duration=STEP_DURATION)
        print("[Player] 樂句播放結束\n")

# ====== 主程式 ======
if __name__ == "__main__":
    print("🎵 自動旋律生成與播放系統啟動中...")
    gen_thread = threading.Thread(target=generator_thread, daemon=True)
    play_thread = threading.Thread(target=player_thread, daemon=True)

    gen_thread.start()
    play_thread.start()

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n結束中...")
        stop_event.set()
        gen_thread.join(timeout=2)
        play_thread.join(timeout=2)
        print("已安全退出")
        player.player.close()
