# melodic_generator.py
"""
MelodicGenerator (v_dynamic_scale)

- 每一步以 prev_note 為基準，建立一個臨時 scale（major 或 minor），範圍為 prev_note ± 12 半音（±1 octave）。
- 候選先從臨時 scale 取出（若範圍內找不到會退回整個 scale 範圍），
  並對位於當前和弦的候選提高權重 (chord_weight_mul)。
- 柏林噪音 (pnoise1) 仍用於每小節的整體趨勢（target_pitch），並納入權重以引導整體方向。
- sustain_probs 用盡後為 0.5。
- debug=True 會逐步印出候選與選中音符，方便檢查流程。
"""

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


# scale interval patterns
MAJOR_INTERVALS = [0, 2, 4, 5, 7, 9, 11]  # semitones from tonic
MINOR_INTERVALS = [0, 2, 3, 5, 7, 8, 10]  # natural minor


# ======== 主旋律生成器 ========
class MelodicGenerator:
    def __init__(
        self,
        mode: str = "major",          # "major" or "minor"
        base_note: int = 60,          # 起始 prev note
        total_steps: int = 128,
        steps_per_bar: int = 16,
        max_span_semitones: int = 12, # 1 octave 用於 trend scaling (也用作範圍)
        max_step_jump: int = 5,
        sustain_probs: List[float] = [0.96, 0.95, 0.94, 0.92, 0.90, 0.88, 0.73, 0.6],
        rest_prob: float = 0.05,
        trend_strength: float = 0.4,
        chord_change_every: int = 16,
        chord_weight_mul: float = 1.5,   # 和弦內音候選權重乘數
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
        self.sustain_probs = sustain_probs or [0.96, 0.95, 0.94, 0.92, 0.90, 0.88, 0.73, 0.6]
        self.rest_prob = rest_prob
        self.trend_strength = trend_strength
        self.chord_change_every = chord_change_every
        self.chord_weight_mul = chord_weight_mul
        self.debug = debug

        # init chord function
        self.current_function = "tonic"
        self.current_chord, self.current_chord_notes = random.choice(chord_library[self.current_function])

    # 產生以 tonic 為基礎的 scale notes（在多個八度內）
    def _build_temp_scale(self, tonic: int) -> List[int]:
        """
        以 tonic (MIDI int) 為主音，回傳該調在 tonic-12 .. tonic+12 範圍內的音列表。
        使用 major 或 minor pattern 由 self.mode 決定。
        """
        intervals = MAJOR_INTERVALS if self.mode == "major" else MINOR_INTERVALS
        notes = set()

        low_bound = tonic - 12
        high_bound = tonic + 12

        # 產生 -1 octave, 0, +1 octave 的音
        for octave in (-12, 0, 12):
            base = tonic + octave
            for iv in intervals:
                n = base + iv
                if low_bound <= n <= high_bound:
                    notes.add(n)

        # 也加入 tonic 本身（保險）
        if tonic >= low_bound and tonic <= high_bound:
            notes.add(tonic)

        return sorted(notes)

    def _next_chord(self):
        next_func = random.choice(chord_progression_rules[self.current_function])
        chord_name, chord_notes = random.choice(chord_library[next_func])
        self.current_function = next_func
        self.current_chord = chord_name
        self.current_chord_notes = chord_notes
        return chord_notes

    def generate_phrase_grid(self) -> List[int]:
        """
        回傳 grid（長度 self.total_steps），-1 = rest，其他為 MIDI note int。
        流程：
          - 每小節用 pnoise1 生成一個 trend 偏移 (半音)，影響 target_pitch
          - 每 step 以 prev_note 為中心建立臨時 scale（±12），從中取候選
          - 若候選包含和弦音，和弦音在權重上乘 self.chord_weight_mul
          - 權重基底以距離 prev_note 的倒數，超過 max_step_jump 的跳躍權重被打折
          - 同音延續依 sustain_probs 控制（用盡後 0.5）
        """
        grid = [-1] * self.total_steps
        bars = max(1, self.total_steps // self.steps_per_bar)

        # 柏林噪音 -> 每小節一個值（近似 -1..1），再 scale 到半音偏移
        noise_values = [pnoise1(i * 0.2) for i in range(bars)]
        noise_scaled = [v * self.trend_strength * self.max_span_semitones for v in noise_values]

        prev_note = self.base_note

        for step in range(self.total_steps):
            bar_idx = step // self.steps_per_bar
            current_offset = noise_scaled[bar_idx]
            target_pitch = int(round(self.base_note + current_offset))

            # 換和弦
            if step % self.chord_change_every == 0 and step != 0:
                chord_notes = self._next_chord()
                if self.debug:
                    print(f"\n>> step {step}: chord -> {self.current_chord} {chord_notes}")
            else:
                chord_notes = self.current_chord_notes

            # 休止判定
            if random.random() < self.rest_prob:
                grid[step] = -1
                if self.debug:
                    print(f"Step {step:03d} | Bar {bar_idx+1} | REST")
                continue

            # build temporary scale around prev_note ±12
            temp_scale = self._build_temp_scale(self.base_note)  # list of MIDI ints within ±1 octave

            # candidates: those temp_scale notes (we prefer these)
            candidates = [n for n in temp_scale if abs(n - prev_note) <= self.max_span_semitones]

            # if somehow empty (shouldn't), fallback to chord notes within ±1 octave then full chord
            if not candidates:
                candidates = [n for n in chord_notes if abs(n - prev_note) <= self.max_span_semitones]
            if not candidates:
                candidates = chord_notes.copy()

            # compute weights
            weights = []
            for n in candidates:
                dist = abs(n - prev_note)
                # base weight prefers small step
                w = 1.0 / (1 + dist)
                # big jumps reduced
                if dist > self.max_step_jump:
                    w *= 0.1
                # chord bias: if candidate is in current chord, boost weight
                if n in chord_notes:
                    w *= self.chord_weight_mul
                # trend bias: favor notes closer to target_pitch (soft bias)
                trend_dist = abs(n - target_pitch)
                # map trend influence: closer to target → small bonus
                trend_bonus = max(0.0, (self.max_span_semitones - trend_dist) / (self.max_span_semitones)) * (self.trend_strength)
                w *= (1.0 + trend_bonus)
                weights.append(w)

            # normalize and choose
            total_w = sum(weights)
            if total_w <= 0:
                note = random.choice(candidates)
            else:
                probs = [w / total_w for w in weights]
                note = random.choices(candidates, probs)[0]

            grid[step] = note
            if self.debug:
                print(f"Step {step:03d} | Bar {bar_idx+1} | prev={prev_note} target={target_pitch:+d} "
                      f"| temp_scale={temp_scale} | candidates={candidates} | chosen={note} | weights={['{:.3f}'.format(x) for x in weights]}")

            prev_note = note

            # sustain extension
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

    def generate_phrase(self, show_plot: bool = True, debug: bool = False):
        orig_debug = self.debug
        if debug:
            self.debug = True

        grid = self.generate_phrase_grid()

        if debug:
            # restore debug prints after generation
            self.debug = orig_debug

        print("Generated Grid (first 64 steps):")
        print(grid[:64])

        if show_plot:
            plt.figure(figsize=(12, 4))
            xs = [i for i, n in enumerate(grid) if n != -1]
            ys = [n for n in grid if n != -1]
            plt.plot(xs, ys, marker='o', linestyle='-')
            plt.title(f"Generated Melody (mode={self.mode})")
            plt.xlabel("Step (1 step = 1/16 note)")
            plt.ylabel("MIDI Pitch")
            plt.grid(True)
            plt.show()

        return grid


# ===== 測試範例 =====
if __name__ == "__main__":
    mg = MelodicGenerator(
        mode="major",
        base_note=60,
        total_steps=64,
        steps_per_bar=16,
        trend_strength=0.5,
        rest_prob=0.05,
        chord_change_every=16,
        chord_weight_mul=1.5,
        debug=True,
        seed=42
    )
    grid = mg.generate_phrase(show_plot=True, debug=True)
