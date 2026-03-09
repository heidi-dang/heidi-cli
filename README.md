# 🤖 Heidi CLI: The "Brain" for Your Local AI

Listen, we've all been there. You've got a shiny new LLM running on your laptop, but it's basically a goldfish. It forgets what it did five minutes ago, and it keeps making the same dumb mistakes. 

Enter **Heidi CLI**. 

Heidi is the command-center for the **Unified Learning Suite**. It’s not just some fancy wrapper for an API; it’s a full-on "Closed-Loop Learning System." Basically, it’s a way to turn those generic AI models into specialized, self-improving agents that actually learn from their own successes and failures. It’s like a personal trainer, but for your LLMs.

---

### 🛠 How the Magic Actually Happens (The 4-Phase Loop)

Think of Heidi like a "Perception-Action-Learning" loop. She’s got five internal modules that play together like a well-oiled (and slightly sarcastic) machine:

#### 1. The Multi-Model Host (`src/model_host`)
Stop talking to the cloud! Heidi hosts your models right here on your machine (shoutout to Ollama and local transformers). 
*   **What it does:** Gives you a unified, OpenAI-compatible API (`/v1/chat/completions`).
*   **The "Secret Sauce":** You can route requests to different models—like a "stable" one for real work and an "experimental" one for when you’re feeling spicy—without ever touching your app code.

#### 2. Runtime Learning & Memory (`src/runtime`)
Heidi doesn't like starting from zero every time.
*   **What it does:** Uses a SQLite database for both short-term "what just happened?" and long-term "wait, I remember this!" memory.
*   **The "Secret Sauce":** Once a task is done, the **Reflection Engine** kicks in. It scores how well it did (Reward Scoring) and saves the "pro-tips" that worked. Next time you ask something similar, Heidi whispers those successful strategies back into the prompt. It’s basically cheating, but legal.

#### 3. The Data Pipeline (`src/pipeline`)
Clean data = happy AI. 
*   **What it does:** Grabs every single interaction and stuffs them into dated "Run Folders."
*   **The "Secret Sauce":** A **Curation Engine** digests these runs, tosses the garbage, and applies a **Secret Redaction Layer**. It scrubs your OpenAI keys, deep-rooted secrets, and embarrassing passwords before they ever touch the retraining loop. Privacy is cool, okay?

#### 4. Registry & Atomic Hot-Swap (`src/registry`)
When you’ve got enough data, it’s time to level up.
*   **What it does:** Manages a **Model Registry** with stable and candidate channels (think of it like "Production" vs. "Beta"). 
*   **The "Secret Sauce":** After retraining, an **Eval Harness** checks if the new model is actually better or if it's just hallucinating harder. If it passes the test, Heidi does an **Atomic Hot-Swap**—reloading the new model in milliseconds with zero downtime. 

---

### 🚀 Commands You’ll Actually Use

| Feature | The Command | What's it for? |
| :--- | :--- | :--- |
| **Model Hosting** | `heidi model serve` | Spins up the local server. Easy peasy. |
| **Agent Memory** | `heidi memory search` | Digging through the agent's brain for that one thing. |
| **Reflection** | `heidi learning reflect` | Forces the agent to think about what it just did. |
| **Data Export** | `heidi learning export` | Bags up the curated/redacted data for retraining. |
| **Promotion** | `heidi learning promote` | Moves a "Candidate" model to "Stable" status. |
| **System Health** | `heidi doctor` | Makes sure everything isn't on fire. |

---

### 🌍 Why does the AI Community even care?

Let’s be real, the current AI world is a bit of a mess. Heidi fixes the big headaches:

1.  **Privacy is King:** Most learning happens in the cloud. Nope. Heidi keeps your training data, your memory, and your weights 100% on your machine. Your company secrets stay *your* secrets.
2.  **Stopping the "Stupid Loop":** We’ve all seen agents make the same mistake twice. Heidi’s **Redaction & Reflection** layers make sure the model actually gets *better* at your specific job, not just weirder.
3.  **MLOps for the rest of us:** Usually, you need a team of engineers to build retraining pipelines. Heidi abstracts all that noise into a single CLI tool. Now you can run a professional-grade Model Lab from your bedroom.

---

### 📦 How to get this thing running

**1. Install the bits:**
```bash
python -m pip install -e '.[dev]'
```

**2. Check the vitals:**
```bash
# This makes sure your state/ directories and docs are alive
heidi doctor
```

**3. Fire it up:**
```bash
# Start the host and wait for the "Serving" message
heidi model serve
```

**4. Check your status:**
```bash
heidi status
```

---
*Heidi is written by humans (mostly) to help machines act more like humans (the smart ones).*
