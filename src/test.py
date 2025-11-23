# melodic_generator.py
"""
MelodicGenerator (Optimized v2)

優化內容：
1. 全域調性鎖定 (Global Scale)：解決音準漂移問題，確保所有音符符合設定的調性。
2. 節奏感知 (Rhythm Awareness)：在重拍 (Strong Beat) 強制偏好和弦音，弱拍允許經過音。
3. 趨勢引導 (Trend Guidance)：保留柏林噪音作為旋律起伏的參考線。
4. 結構優化：加入距離懲罰與樂句結尾回歸主音的傾向。
"""

import random
from typing import List, Set
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
    "tonic": ["tonic", "subdominant", "subdominant", "dominant"],
    "subdominant": ["subdominant", "dominant", "tonic"],
    "dominant": ["tonic", "tonic", "subdominant"]
}


MAJOR_INTERVALS = {0, 2, 4, 5, 7, 9, 11}
MINOR_INTERVALS = {0, 2, 3, 5, 7, 8, 10}

# ======== 主旋律生成器 ========
class MelodicGenerator:
    def __init__(
        self,
        mode: str = "major",          # "major" or "minor"
        base_note: int = 60,          # Key Center (e.g., C4)
        total_steps: int = 128,
        steps_per_bar: int = 16,
        max_span_semitones: int = 12, # 用於 trend scaling
        max_step_jump: int = 7,       # 允許的最大跳躍度數
        sustain_probs: List[float] = [0.96, 0.95, 0.94, 0.92, 0.90, 0.88, 0.73, 0.6],
        rest_prob: float = 0.05,
        trend_strength: float = 0.4,
        chord_change_every: int = 16,
        chord_weight_mul: float = 1.5,
        debug: bool = False,
        seed: int = 1
    ):
        if seed is not None:
            random.seed(seed)

        assert mode in ("major", "minor")
        self.mode = mode
        self.base_note = base_note
        self.total_steps = total_steps
        self.steps_per_bar = steps_per_bar
        self.max_span_semitones = max_span_semitones
        self.max_step_jump = max_step_jump
        self.sustain_probs = sustain_probs
        self.rest_prob = rest_prob
        self.trend_strength = trend_strength
        self.chord_change_every = chord_change_every
        self.chord_weight_mul = chord_weight_mul
        self.debug = debug

        # init chord function
        self.current_function = "tonic"
        self.current_chord, self.current_chord_notes = random.choice(chord_library[self.current_function])

        # 初始化全域音階 (Global Scale)，鎖定調性
        self.global_scale = self._build_global_scale()

    def _build_global_scale(self) -> List[int]:
        """建立全曲可用的安全音符池 (範圍 ±2 八度)，確保不走音"""
        intervals = MAJOR_INTERVALS if self.mode == "major" else MINOR_INTERVALS
        valid_notes = []
        # 範圍：從 base_note 往下 24 半音 到 往上 24 半音
        for i in range(self.base_note - 24, self.base_note + 25):
            degree = (i - self.base_note) % 12
            if degree in intervals:
                valid_notes.append(i)
        return sorted(valid_notes)

    def _next_chord(self):
        next_func = random.choice(chord_progression_rules[self.current_function])
        chord_name, chord_notes = random.choice(chord_library[next_func])
        self.current_function = next_func
        self.current_chord = chord_name
        self.current_chord_notes = chord_notes
        return chord_notes

    def _is_chord_tone(self, note: int, chord_notes: List[int]) -> bool:
        """判斷是否為當前和弦音 (忽略八度)"""
        return (note % 12) in [(n % 12) for n in chord_notes]

    def generate_phrase_grid(self) -> List[int]:
        """
        核心生成
        """
        grid = [-1] * self.total_steps
        bars = max(1, self.total_steps // self.steps_per_bar)

        # 柏林噪音 -> Trend
        noise_values = [pnoise1(i * 0.2) for i in range(bars)]
        noise_scaled = [v * self.trend_strength * self.max_span_semitones for v in noise_values]

        prev_note = self.base_note

        for step in range(self.total_steps):
            bar_idx = step // self.steps_per_bar
            pos_in_bar = step % self.steps_per_bar
            
            # 重拍判斷 (假設 4/4 拍，每 4 步為一拍)
            is_strong_beat = (pos_in_bar % 4 == 0)

            current_offset = noise_scaled[bar_idx]
            target_pitch = int(round(self.base_note + current_offset))

            # 換和弦
            if step % self.chord_change_every == 0 and step != 0:
                chord_notes = self._next_chord()
                if self.debug:
                    print(f"\n>> step {step}: chord -> {self.current_chord} {chord_notes}")
            else:
                chord_notes = self.current_chord_notes

            # 休止判定 (重拍時稍微降低休止機率)
            current_rest_prob = self.rest_prob * 0.2 if is_strong_beat else self.rest_prob
            if random.random() < current_rest_prob:
                grid[step] = -1
                continue

            # 候選音從 Global Scale 中篩選，而非相對音階
            # 找出所有在 global_scale 中，且距離 prev_note 不太遠的音
            candidates = [
                n for n in self.global_scale 
                if abs(n - prev_note) <= self.max_step_jump
            ]
            
            # Fallback (極端情況)
            if not candidates: 
                candidates = [prev_note]

            # 計算權重 (Weight Calculation)
            weights = []
            for n in candidates:
                w = 1.0
                dist = abs(n - prev_note)
                is_ct = self._is_chord_tone(n, chord_notes)

                # A. 距離權重：越近越好 (Stepwise motion)
                w *= (1.0 / (1.0 + dist * 0.65))

                # B. 和弦音與重拍規則
                if is_strong_beat:
                    if is_ct:
                        w *= 5.0  # 重拍極度偏好和弦音 (骨幹)
                    else:
                        w *= 0.1  # 重拍很不喜歡非和弦音
                else:
                    # 弱拍
                    if is_ct:
                        w *= 1.5  # 還是喜歡和弦音
                    else:
                        w *= 0.8  # 但對經過音比較寬容

                # C. Trend Bias: 獎勵靠近 Noise 趨勢的音
                trend_dist = abs(n - target_pitch)
                if trend_dist < 5:
                    w *= 1.2
                
                # D. 樂句結尾回歸
                # 如果是 bar 的最後一步，且是主音 (Tonic)，加分
                if pos_in_bar == self.steps_per_bar - 1:
                    if n % 12 == self.base_note % 12:
                        w *= 2.0

                weights.append(w)

            # 選擇音符
            total_w = sum(weights)
            if total_w <= 0:
                note = random.choice(candidates)
            else:
                note = random.choices(candidates, weights=weights, k=1)[0]

            grid[step] = note
            
            if self.debug:
                print(f"Step {step:03d} | Bar {bar_idx+1}.{pos_in_bar} | Strong={is_strong_beat} | "
                      f"Chord={self.current_chord} | Chosen={note}")

            prev_note = note

            # Sustain Extension (延音邏輯)
            # 重拍通常是新音符的開始，所以我們避免讓前一個音「跨過」重拍延續下來 (除非刻意切分音，這裡先簡化)
            sustain_run = 0
            j = 1
            while (step + j) < self.total_steps:
                next_is_strong = ((step + j) % self.steps_per_bar) % 4 == 0
                
                # 如果下一個是重拍，強迫停止延音 (讓重拍重新觸發新音符)
                if next_is_strong: 
                    break

                prob_idx = sustain_run
                p_same = self.sustain_probs[prob_idx] if prob_idx < len(self.sustain_probs) else 0.5
                
                if random.random() < p_same:
                    grid[step + j] = note
                    sustain_run += 1
                    j += 1
                else:
                    break

        return grid

    def generate_phrase(self, show_plot: bool = True, debug: bool = False):
        orig_debug = self.debug
        if debug:
            self.debug = True

        grid = self.generate_phrase_grid()

        if debug:
            self.debug = orig_debug

        print("\nGenerated Grid (first 64 steps):")
        print(grid[:64])

        if show_plot:
            plt.figure(figsize=(12, 4))
            xs = [i for i, n in enumerate(grid) if n != -1]
            ys = [n for n in grid if n != -1]
            
            # 畫出旋律點
            plt.plot(xs, ys, marker='o', linestyle='-', label='Melody')
            
            # 畫出基準線 (Base Note)
            plt.axhline(y=self.base_note, color='r', linestyle='--', alpha=0.3, label='Base Note')
            
            plt.title(f"Optimized Generated Melody (mode={self.mode})")
            plt.xlabel("Step (1 step = 1/16 note)")
            plt.ylabel("MIDI Pitch")
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.show()

        return grid


# ===== 測試範例 =====
if __name__ == "__main__":
    mg = MelodicGenerator(
        mode="major",
        base_note=60,         # C4
        total_steps=64,       # 4 小節
        steps_per_bar=16,
        trend_strength=0.5,
        rest_prob=0.05,
        chord_change_every=16,
        debug=True,
        seed=42
    )
    grid = mg.generate_phrase(show_plot=True, debug=True)