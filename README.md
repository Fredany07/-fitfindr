# FitFindr

An AI-powered multi-tool agent that helps users find secondhand clothing and figure out how to wear it. FitFindr takes a natural language query, searches a mock listings dataset, suggests outfit combinations based on the user's wardrobe, and generates a shareable social media caption — all in one automated workflow.

---

## Setup

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root with your Groq API key (free at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

Run the app:
```bash
python app.py
```

Then open the URL shown in your terminal (usually `http://localhost:7860`).

---

## Tool Inventory

### Tool 1: `search_listings`

**Function signature:**
```python
search_listings(description: str, size: str | None = None, max_price: float | None = None) -> list[dict]
```

**Inputs:**
- `description` (str): Keywords describing the item the user wants (e.g. "vintage tee")
- `size` (str | None): Clothing size to filter by, or None to skip size filtering
- `max_price` (float | None): Maximum price inclusive, or None to skip price filtering

**Output:** A list of matching listing dicts sorted by relevance (highest keyword overlap first). Each dict contains: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`. Returns an empty list if nothing matches.

**Purpose:** Searches the mock listings dataset by scoring each listing on keyword overlap with the description, then filtering by size and price.

---

### Tool 2: `suggest_outfit`

**Function signature:**
```python
suggest_outfit(new_item: dict, wardrobe: dict) -> str
```

**Inputs:**
- `new_item` (dict): A listing dict — the item the user is considering buying
- `wardrobe` (dict): A wardrobe dict with an `items` key containing a list of wardrobe item dicts. May be empty.

**Output:** A non-empty string with 1–2 complete outfit suggestions. If the wardrobe is empty, returns general styling advice instead of crashing.

**Purpose:** Calls the Groq LLM (llama-3.3-70b-versatile) to generate outfit combinations using the new item and the user's existing wardrobe pieces.

---

### Tool 3: `create_fit_card`

**Function signature:**
```python
create_fit_card(outfit: str, new_item: dict) -> str
```

**Inputs:**
- `outfit` (str): The outfit suggestion string returned by `suggest_outfit`
- `new_item` (dict): The listing dict for the thrifted item

**Output:** A 2–4 sentence Instagram/TikTok-style caption mentioning the item name, price, and platform. Returns a descriptive error string if `outfit` is empty — does not raise an exception.

**Purpose:** Calls the Groq LLM at temperature 1.0 to generate a casual, authentic social media caption that varies across different inputs.

---

## How the Planning Loop Works

The planning loop in `run_agent()` follows this conditional logic:

1. **Parse the query** — extract `description`, `size`, and `max_price` from the natural language input using regex. No LLM needed for this step.

2. **Call `search_listings`** — if the result is an empty list, set `session["error"]` to a helpful message and return immediately. `suggest_outfit` is never called with empty input.

3. **Select the top result** — store `results[0]` as `session["selected_item"]`.

4. **Call `suggest_outfit`** — only reached if search returned results. Store the output as `session["outfit_suggestion"]`.

5. **Call `create_fit_card`** — only reached if suggest_outfit succeeded. Store the output as `session["fit_card"]`.

6. **Return the session** — the UI reads from the session dict to populate the three output panels.

The agent's behavior changes based on what `search_listings` returns — if results are empty, the workflow terminates early and the outfit and fit card panels stay blank.

---

## State Management

All state is stored in a single `session` dictionary initialized at the start of each `run_agent()` call. The session tracks:

- `query` (str): The original user input
- `parsed` (dict): Extracted description, size, and max_price
- `search_results` (list): All matching listings returned by `search_listings`
- `selected_item` (dict): The top result — passed directly into `suggest_outfit`
- `wardrobe` (dict): The user's wardrobe — passed into `suggest_outfit`
- `outfit_suggestion` (str): The string returned by `suggest_outfit` — passed directly into `create_fit_card`
- `fit_card` (str): The final caption returned by `create_fit_card`
- `error` (str | None): Set if the workflow ended early; None on success

No data is re-entered by the user between steps. Each tool receives its inputs directly from the session populated by the previous tool.

---

## Interaction Walkthrough

**User query:** `"looking for a vintage tee under $30"`

**Step 1 — Tool called: `search_listings`**
- Input: `description="vintage tee"`, `size=None`, `max_price=30.0`
- Why this tool: The user provided a description and a price ceiling. This is always the first tool called — it finds the item before anything else can happen.
- Output: A list of matching listings. Top result: `Vintage Band Tee — Faded Grey, $19, Depop, Good condition`

**Step 2 — Tool called: `suggest_outfit`**
- Input: `new_item=<Vintage Band Tee dict>`, `wardrobe=<example wardrobe with 10 items>`
- Why this tool: Search returned a result, so the agent proceeds to styling. The selected item and wardrobe are passed directly from the session.
- Output: `"Pair this tee with your wide-leg jeans and chunky sneakers for a classic 90s grunge look. Layer with your vintage denim jacket for added edge."`

**Step 3 — Tool called: `create_fit_card`**
- Input: `outfit=<suggestion string>`, `new_item=<Vintage Band Tee dict>`
- Why this tool: Both prior tools succeeded, so the agent generates the shareable caption as the final step.
- Output: `"thrifted this faded band tee for $19 on Depop and it's giving everything 🖤 paired it with wide-leg denim and chunky sneakers for that effortless 90s vibe"`

**Final output to user:**
- Panel 1 (Listing): Title, price, platform, size, condition, colors, style tags
- Panel 2 (Outfit): The full outfit suggestion with styling tips
- Panel 3 (Fit Card): The Instagram-style caption

---

## Error Handling and Fail Points

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No listings match the query | Sets `session["error"] = "No listings found matching your search. Try adjusting your description, removing the size filter, or increasing your budget."` Returns immediately — `suggest_outfit` is never called. |
| `suggest_outfit` | Wardrobe is empty (`wardrobe["items"] == []`) | Switches to a general styling prompt and returns advice like `"No wardrobe data found. Here are some general styling tips for your item..."` — does not raise an exception. |
| `create_fit_card` | `outfit` is an empty or whitespace-only string | Returns `"Could not generate fit card — outfit description was missing. Please try your search again."` — does not raise an exception. |

**Concrete example from testing:**
```bash
python -c "from tools import create_fit_card, search_listings; r = search_listings('vintage tee', max_price=50); print(create_fit_card('', r[0]))"
# Output: Could not generate fit card — outfit description was missing. Please try your search again.
```

---

## Spec Reflection

**One way planning.md helped during implementation:**
The planning loop section of planning.md was the most directly useful part of the spec. Because I had written out the exact conditional logic — "if results is empty, set session['error'] and return early; otherwise store results[0] and proceed" — implementing `run_agent()` was straightforward. There was no ambiguity about what the function should do in each case. The diagram also made it easy to verify the implementation matched the design.

**One divergence from the spec, and why:**
In planning.md I described the query parser as extracting a description by removing price and size fragments. In practice, the regex approach required more cleanup than anticipated — filler words like "looking for", "I want", and "find me" were left in the description and reduced search accuracy. I added a filler-word removal step that wasn't in the original spec to fix this. The core logic stayed the same, but the parser ended up more detailed than planned.

---

## AI Usage

**Instance 1 — Implementing `search_listings`:**
I provided Claude with the Tool 1 block from planning.md (inputs, return value, failure mode) and asked it to implement the function using `load_listings()` from the data loader. The generated code correctly filtered by price and size, but the keyword scoring initially used an exact match instead of substring matching. I changed `keyword == word` to `keyword in searchable` so that partial matches (e.g. "tee" matching "tees") would work. I also added the filler-word cleanup to `_parse_query` after noticing search accuracy dropped when queries included phrases like "looking for".

**Instance 2 — Implementing the planning loop:**
I provided Claude with the Planning Loop, State Management, and Architecture sections of planning.md — including the full ASCII diagram — and asked it to implement `run_agent()`. The generated code matched the spec closely, but initially called all three tools unconditionally regardless of whether `search_listings` returned results. I revised the early-return branch to check `if not results` and return the session immediately, which is what the diagram specified.
This is important
