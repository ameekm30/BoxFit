# BoxFit

BoxFit helps shipping-store employees pick the right box at the counter. It was built for a UPS Store in Alameda, CA.

## The problem
After measuring an item, an employee still has to work out the padding, which way the item fits, and which of 20+ boxes is the tightest fit, all in their head while the customer waits. A box that's too small means repacking. A box that's too big costs the customer more, and nobody notices.

## What it does
The employee enters each item's length, width, height, whether it's foldable, its fragility (none / fragile / extra), and a short description. BoxFit returns the three best boxes from the store's real inventory, plus packing instructions and a suggested add-on service.

- **Separate items:** each item gets its own box.
- **Identical items together:** the items are stacked, then boxed.
- **Different items together:** Claude estimates their combined size, then Python picks the box.
- **Nothing fits:** BoxFit tries joining two boxes into one taller box (telescoping).

## How it works: "Claude judges, Python decides"
**Claude (Anthropic API) handles judgment:**
- reads the description to suggest padding, write packing instructions and recommend an add-on
- checks the employee's fragility choice and warns if it disagrees
- estimates the combined size of different items shipped together
- reads the store's price sheet into a box inventory (`inventory_parser.py`)

**Python handles every decision:**
- enforces a minimum padding for each fragility level, so Claude can't under-pad an item
- adds padding to the item's dimensions (`add_buffer`)
- sorts dimensions largest to smallest so every orientation is considered (`sorted_dims`)
- ranks fitting boxes by least wasted space and returns the top 3 (`rank_boxes`)
- stacks identical items (`stack_identical`) and joins two boxes when nothing fits (`telescoping`)

During a lookup, Claude never sees the inventory, never picks the box, and never sets the price.

## Run it
You need Python 3 and an Anthropic API key.

```
git clone https://github.com/ameekm30/BoxFit.git
cd BoxFit
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a file named `.env` in the project folder containing:
```
ANTHROPIC_API_KEY=your-key-here
```

Start the web app:
```
python -m streamlit run app.py
```

Or run the command-line version:
```
python box_fit_algorithm.py
```

## Files
| File                                  | What it is                                                    |
|---------------------------------------|---------------------------------------------------------------|
| `app.py`                              | Web interface (Streamlit)                                     |
| `box_fit_algorithm.py`                | Box-fitting algorithm, Claude functions, command-line version |
| `inventory_parser.py`                 | Turns a store's price sheet into a box inventory              |
| `chat_helpers.py`, `claude_client.py` | Claude API setup and helpers                                  |
| `test_inventory.csv`                  | The store's box sizes and prices in CSV format                |
| `boxes.xlsx`  | The store's box sizes and prices in XLSX format               |

## Known limitations
- Ranking by least wasted space can pick a long, narrow box (for example, 12×12×48 for three books) because it has less total volume. Version 2 will also weigh box price and how much fill the empty space needs.
- Foldable items always get 1 inch of padding, even when fragile.
- Claude's combined-size estimates can vary between runs.
- Telescoping only extends height.

## AI use
Claude runs inside the app as described above. While building, Claude acted as a tutor: it asked questions, explained concepts, reviewed code, and helped with bug fixes. Claude didn’t give me code or logic, with two exceptions: it wrote the Streamlit interface setup in app.py, and a few times it showed me corrected lines for bugs in my own code, which I typed in myself. Claude also helped write this README.
