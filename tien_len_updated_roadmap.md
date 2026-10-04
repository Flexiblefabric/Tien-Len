> **Historical document:** This June 2025 roadmap is retained for project history. It has been superseded by [ROADMAP.md](ROADMAP.md) and [docs/CURRENT_STATE_AUDIT.md](docs/CURRENT_STATE_AUDIT.md).

# 🎯 Tiến Lên Game — Integrated Development Roadmap

This roadmap merges the original feature plan with updated insights from the current state analysis and visual roadmap (2025). It is organized by **design areas** for clarity and modular implementation.

---

## 🎨 Visual & Layout System

| Feature | Description | Status |
|--------|-------------|--------|
| **Color-coded Glow Effects** | Replace labels on pile cards with subtle glow effects matching player identity. | ✅ Implemented |
| **Dynamic Card Spacing** | Adjust hand spacing based on window width and hand size. | 🔄 In Progress |
| **Player Layout Refinement** | Position AI players around the board realistically (top, left, right). | ✅ Done |
| **Card Fan or Arc Layout** | Fan out large hands to improve visibility and reduce overlap. | 🔜 Planned |
| **Responsive UI Scaling** | Support layout scaling for different resolutions and window sizes. | 🔜 Planned |

---

## 🧠 Game Mechanics & AI

| Feature | Description | Status |
|--------|-------------|--------|
| **AI Personalities** | Add unique behaviors (aggressive, defensive, bluffing). | 🔄 Partial |
| **Expert AI Lookahead** | Depth-limited minimax for optimal move selection. | 🔜 Planned |
| **Hint System** | Provide hint suggestions based on AI scoring logic. | 🔜 Planned |
| **AI Name Color Coding** | Ensure each AI has a unique color for glow and scoreboard UI. | ✅ Done |
| **Custom Rule Toggles** | In-game toggles for "2 in sequences", bombs, tu quy. | 🔜 Planned |

---

## 🔊 Feedback & Interaction

| Feature | Description | Status |
|--------|-------------|--------|
| **Audio Feedback** | Sound effects for plays (single, pair, bomb). | 🔜 Planned |
| **Music System** | Background tracks for gameplay and round transitions. | 🔜 Planned |
| **Animated Glows** | Subtle pulsing or fading glow to indicate current plays. | 🔜 Planned |
| **Card Flip Animation** | Visual feedback when AI plays to the pile. | 🔜 Planned |

---

## 📊 Stats, Progress & Quality of Life

| Feature | Description | Status |
|--------|-------------|--------|
| **Scoreboard UI** | Track round wins and cards remaining per player. | ✅ Implemented |
| **Player Stats Tracking** | Games played/won, average hand strength, etc. | 🔜 Planned |
| **Game Summary View** | Visual summary of the previous round's combos. | 🔜 Planned |
| **Undo / Replay System** | Step back through snapshots or replay a round. | 🔜 Planned |
| **Save & Resume** | Persistent game sessions between runs. | 🔜 Planned |

---

## 🧪 Testing & Packaging

| Feature | Description | Status |
|--------|-------------|--------|
| **Automated Tests** | Unit tests for combo logic, scoring, AI behavior. | 🔜 Planned |
| **Performance Optimizations** | Lazy rendering, frame capping, efficient image caching. | 🔄 Partial |
| **Executable Build** | Export as `.exe` or app via PyInstaller. | 🔜 Planned |

---

## 📅 Development Timeline (Suggested)

| Week | Focus |
|------|-------|
| 1 | Finalize visual layout and glow system |
| 2–3 | Implement AI strategies and rule toggles |
| 4 | Add animations, sound effects, and player stats |
| 5+ | Introduce save/load, multiplayer, and final polish |

---

_Last updated: June 2025_