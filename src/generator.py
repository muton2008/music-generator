# melodic_generator.py
import random
from typing import List
from noise import pnoise1
import matplotlib.pyplot as plt

# ======== 和弦庫與進行規則 ========
chord_library = {
    "tonic": [
        ("C",  [60, 64, 67]),  # C
        ("Am", [57, 60, 64]),  # Am
        ("Em", [52, 55, 59]),  # Em
    ],
    "subdominant": [
        ("F",  [53, 57, 60]),  # F
        ("Dm", [50, 53, 57]),  # Dm
    ],
    "dominant": [
        ("G",   [55, 59, 62]),  # G
        ("G7",  [55, 59, 62, 65]),
        ("Bdim",[59, 62, 65]),
    ],
}

chord_progression_rules = {
    "tonic": ["tonic", "subdominant"],
    "subdominant": ["subdominant", "dominant"],
    "dominant": ["tonic"]
}


# ======== 主旋律生成器 ========
class MelodicGenerator:
    def __init__(
        self,
        scale_notes: List[int],        # 音階 (例: C大調 [60,62,64,65,67,69,71,72])
        base_note: int = 60,           # 旋律中心
        total_steps: int = 128,        # 樂句長度
        steps_per_bar: int = 16,       # 每小節的 step 數（相當於16分音符數）
        max_span_semitones: int = 12,  # 音域範圍
        max_step_jump: int = 5,        # 每次音高跳動最大距離
        sustain_probs: List[float] = [0.96 ,0.95 ,0.94 ,0.92 , 0.90, 0.88, 0.73, 0.6],
        rest_prob: float = 0.05,       # 休止符機率
        trend_strength: float = 0.4,   # 趨勢強度
        chord_change_every: int = 16   # 每幾個 step 換和弦
    ):
        self.scale_notes = sorted(scale_notes)
        self.base_note = base_note
        self.total_steps = total_steps
        self.steps_per_bar = steps_per_bar
        self.max_span_semitones = max_span_semitones
        self.max_step_jump = max_step_jump
        self.sustain_probs = sustain_probs or [0.96 ,0.95 ,0.94 ,0.92 , 0.90, 0.88, 0.73, 0.6]
        self.rest_prob = rest_prob
        self.trend_strength = trend_strength
        self.chord_change_every = chord_change_every

        self.current_function = "tonic"
        self.current_chord, self.current_chord_notes = random.choice(chord_library[self.current_function])

    def _next_chord(self):
        next_func = random.choice(chord_progression_rules[self.current_function])
        chord_name, chord_notes = random.choice(chord_library[next_func])
        self.current_function = next_func
        self.current_chord = chord_name
        self.current_chord_notes = chord_notes
        return chord_notes

    # ===== 產生樂句 =====
    def generate_phrase_grid(self):
        grid = [-1] * self.total_steps  # -1 代表休止符
        bars = self.total_steps // self.steps_per_bar

        # 產生柏林噪音曲線，控制每小節平均音高偏移
        noise_values = [pnoise1(i * 0.2) for i in range(bars)]
        # 正規化到 [-trend_strength, +trend_strength]
        noise_scaled = [(v * self.trend_strength * self.max_span_semitones) for v in noise_values]

        prev_note = self.base_note

        for step in range(self.total_steps):
            bar_idx = step // self.steps_per_bar
            current_offset = noise_scaled[bar_idx]  # 該小節的趨勢偏移
            target_pitch = self.base_note + current_offset

            # 換和弦
            if step % self.chord_change_every == 0 and step != 0:
                chord_notes = self._next_chord()
            else:
                chord_notes = self.current_chord_notes

            # 休止符機率
            if random.random() < self.rest_prob:
                grid[step] = -1
                continue

            # 找出候選音（在調內或和弦內）
            candidates = [n for n in chord_notes if abs(n - target_pitch) <= self.max_span_semitones]
            if not candidates:
                candidates = [n for n in self.scale_notes if abs(n - target_pitch) <= self.max_span_semitones]
            if not candidates:
                candidates = self.scale_notes

            # 使用距離權重平滑選擇
            weights = [1 / (1 + abs(n - prev_note)) for n in candidates]
            note = random.choices(candidates, weights)[0]
            grid[step] = note
            prev_note = note

            # 延音處理
            sustain_run = 0
            j = 1
            while (step + j) < self.total_steps:
                prob_idx = sustain_run
                p_same = self.sustain_probs[prob_idx] if prob_idx < len(self.sustain_probs) else 0.5
                if random.random() < p_same:
                    grid[step + j] = note
                    sustain_run += 1
                    j += 1
                else:
                    break

        return grid

    # ===== 生成與可視化 =====
    def generate_phrase(self, show_plot=True):
        grid = self.generate_phrase_grid()
        print("Generated Grid (first 64 steps):")
        print(grid[:64])

        if show_plot:
            plt.figure(figsize=(12, 4))
            plt.plot([i for i, n in enumerate(grid) if n != -1],
                     [n for n in grid if n != -1],
                     marker='o', linestyle='-', label="Note Pitch")
            plt.title("Generated Melody (C Major)")
            plt.xlabel("Step (1 step = 1/16 note)")
            plt.ylabel("MIDI Pitch")
            plt.legend()
            plt.grid(True)
            plt.show()

        return grid


# ===== 測試 =====
if __name__ == "__main__":
    C_major_scale = [60, 62, 64, 65, 67, 69, 71, 72]
    mg = MelodicGenerator(
        scale_notes=C_major_scale,
        total_steps=128,
        trend_strength=0.5,
        rest_prob=0.02,
        base_note=60,
        chord_change_every=16
    )
    melody = mg.generate_phrase(show_plot=True)
