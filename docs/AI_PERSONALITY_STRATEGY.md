# AI Personalities (Weighted Biases)

Goal: keep **difficulty** and **personality** orthogonal.

- **Difficulty** controls search budget (breadth/depth, lookahead toggle).
- **Personality** applies *weights* to the evaluator's factors. It never hard-blocks a move; it nudges EV up/down.

## Factors (example)
- `finish_priority`: prefer lines that empty the hand sooner.
- `bomb_risk`: penalize bombing early vs saving for pivotal cuts.
- `lead_aggression`: value taking lead to sculpt endgame.
- `defense_holdouts`: weight of keeping breakers (2s, bombs).
- `sequence_value`: value of maintaining/creating straights/runs.
- `opponent_pressure`: prefer plays that reduce opponents’ options (based on last lead).

## Personalities (suggested defaults)

| Personality | finish_priority | bomb_risk | lead_aggression | defense_holdouts | sequence_value | opponent_pressure |
|-------------|-----------------|-----------|------------------|------------------|----------------|-------------------|
| aggressive  | +0.30           | -0.15     | +0.25            | -0.10            | +0.10          | +0.20             |
| defensive   | +0.15           | +0.20     | -0.10            | +0.25            | +0.10          | +0.05             |
| balanced    | +0.20           | +0.05     | +0.05            | +0.10            | +0.10          | +0.10             |
| random      | jitter(+/−0.2)  | jitter    | jitter           | jitter           | jitter         | jitter            |

*Interpretation*: weights are additive biases on a normalized base score (e.g., 0..1). The evaluator combines base heuristics → `base_score`; the selector adds weighted biases → `final_score` and samples argmax with slight temperature for non-determinism.

## JSON config sketch
```json
{
  "ai": {
    "difficulty": "Normal",
    "lookahead": false,
    "personality": "balanced",
    "weights": {
      "finish_priority": 0.20,
      "bomb_risk": 0.05,
      "lead_aggression": 0.05,
      "defense_holdouts": 0.10,
      "sequence_value": 0.10,
      "opponent_pressure": 0.10
    }
  }
}
```

## Minimal interface
```python
class Evaluator:
    def score(self, state, move) -> float:
        ...

class Selector:
    def choose(self, state, legal_moves, evaluator, weights) -> Move:
        # compute base scores
        # add weighted biases
        # pick move (argmax with tiny temperature)
        ...
```

Start by injecting a `weights` dict where your current evaluator aggregates heuristics. No functional change for defaults; personalities just tweak these weights.
