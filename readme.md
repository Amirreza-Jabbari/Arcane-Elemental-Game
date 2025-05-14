# 🌟 Arcane Elemental Game

A browser-based coding adventure built with **Django**, **Tailwind CSS**, and **JavaScript**. Players harness elemental magic by writing small JavaScript snippets to solve programming “trials,” earn XP & runes, unlock quests, and level up their magical prowess!

---

## 🚀 Features

* **Elemental Trials**
  Write JavaScript to wield Water, Air, Earth, and Fire in puzzle-like coding challenges.

* **AI-Driven Evaluation**
  Submissions are semantically compared to canonical solutions via an LLM (Groq + LLaMA-3.3-70B), scoring on logic rather than text.

* **Progression & Rewards**
  Earn XP to level up skills per element, and collect runes (in-game currency) for perfect or near-perfect solutions.

* **Hints System**
  Spend runes to buy contextual hints for each trial; hints persist across sessions.

* **Quest Campaign**
  Complete a series of branching quests, each with multiple objectives (loops, conditionals, recursion, data structures).

* **Interactive UI**
  Tailwind-powered responsive design, draggable world map overlay, NPC dialogue panels, and history drawers.

* **Leaderboard & Profiles**
  View top scores by element, inspect your skills progression, and customize your avatar.

---

## ⚙️ Getting Started

1. **Clone & activate**

   ```bash
   git clone https://github.com/amirreza-jabbari/arcane-elemental-game.git
   cd arcane-elemental-game
   python -m venv env && source env/bin/activate
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure secrets**

   * In your environment, set `GROQ_API_TOKEN` to your Groq/OpenAI key.

4. **Apply migrations & load data**

   ```bash
   python manage.py migrate
   python manage.py loaddata elements.json regions.json trials.json trial_solutions.json … 
   ```

5. **Run the server**

   ```bash
   python manage.py runserver
   ```

   Browse to [http://localhost:8000/](http://localhost:8000/).

---

## 🎮 How to Play

1. **Register or log in** at the home page.
2. **Enter the Realm** → choose a region by element.
3. **Select an Active Trial** → read its objectives.
4. **Write JavaScript** in the code editor and click **Run**.
5. **View your Score**, **Time**, **Mana Used**, **XP**, and **Runes**.
6. **Buy a Hint** (30 runes) if stuck—hint stays after refresh.
7. **Complete Quests** by finishing all objectives; unlock next quests.

---

## 🤖 Code Evaluation

* **Semantic Matching**:

  * Parse to ASTs, normalize unordered structures, alpha-rename, constant-fold, detect equivalent control flow.
  * Prompt strictly returns `{"similarity": X}`.

* **Scoring**:

  * Similarity × 1000 (min 0, max 1000).
  * ≥ 0.75 (750) is a pass, awards up to 40 runes linearly.

---

## 🛠️ Admin & Customization

* Use Django admin at `/admin/` to manage Trials, Quests, NPCs, etc.
* Edit JSON fixtures for bulk data: `elements.json`, `regions.json`, `trials.json`, `trial_solutions.json`, `dialogues.json`, `quests.json`, `questobjectives.json`, `skills.json`.

---

## Contributing

1. Fork & branch
2. Add tests for new trials or features
3. Submit a PR—relive the magic!

---

## License

MIT © 2025 Amirreza Jabbari
Crafted with 🪄 & ❤️
