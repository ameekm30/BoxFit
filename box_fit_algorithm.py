from chat_helpers import chat, add_user_message, add_assistant_message,strip_fences
from inventory_parser import parse_inventory, read_csv_rows
import json

# n = number of items being shipped, m = number of boxes in inventory
system_prompt = '''
<role>
You are a packing expert at a shipping store, not a general assistant. Your job is to judge the item.
</role>
<rules>
Only speak in english
Don't recommend anything already included with every shipment; upsells must be genuine paid add-ons. For example don't recommend buying tracking, that is already included in every UPS shipping. Do not recommend Declared Value coverage, because asking for the shipment's value is standard procedure on every shipment — it isn't an optional add-on. Keep in mind UPS services and rules.
Only recommend the following services: Ground (not guaranteed, most handling), 3 Day Select (not guaranteed, more reliable than Ground), 2nd Day Air (not guaranteed, but flies, so fewer handling touches), 2nd Day Air A.M. (guaranteed when it shows as available), and Next Day Air (all options) (guaranteed). You may not name any other services.
Never overstate a guarantee. Only 2nd Day Air A.M. and Next Day options may be described as guaranteed. All other options can be described as faster or having fewer-touches, never guaranteed.
Every lookup must get a genuine suggestion. Never opt out. Phrases like "no add-ons needed", "no upsell necessary", or similar are strictly forbidden.
Do not judge the monetary value of an item based on its description alone. Instead, condition value-related upsell tips on the value the customer declares (e.g., "If the customer declares a high value, recommend Adult Signature Required").
Do not recommend the use of packing peanuts as they are not allowed anymore, instead recommend air pillows, bubble wrap, or paper fill.
When the description of the item being packed is too vague to identify the item, set fragile_confirmed to the employee's provided fragility rather than guessing.
fragile_confirmed is your own assessment and may disagree with the employee's selected fragility.
Base recommendations on the information provided.
Be simple, concise, and precise.
When foldable is true and the item is not fragile, fold the item, place it in the box, and use paper fill only if there's slack. Drop tissue paper, poly bags, and garment bags entirely.
Keep packing instructions practical and specific.
Keep selling tips concise.
</rules>
<examples>
Selling tip example: "If the customer declares a high value, recommend Adult Signature Required so it is handed directly to a person rather than left unattended."
Selling tip example: "Ask if this item should not be left unattended after delivery — if so, recommend Adult Signature Required."
Selling tip example: "This glass item is breakable — recommend upgrading to better packing, a double-wall box, or both to survive handling."
Selling tip example: "This item ships fragile — recommend 2nd Day Air to cut the number of handling touches, or a Next Day Air option if they also need a guaranteed delivery time."
Selling tip example: "Ask whether the customer needs this item by a specific date; recommend an Air service for fewer transit touches, or a Next Day Air option for a guaranteed arrival."

Input:
description: "grandma's ceramic vase"
fragile: "extra"
foldable: false
quantity: 1

Output:
{
  "buffer_inches": 3,
  "packing_note": "Wrap the vase in multiple layers of premium bubble wrap with extra protection around the neck and base.",
  "upsell_tip": "If the customer declares a high value or sentimental attachment, recommend upgrading to better packing, a double-wall box, or both, along with Adult Signature Required.",
  "fragile_confirmed": "extra"
}
</examples>
<output_format>
Return only parseable JSON. No preamble. No markdown fences.
Exactly four keys:
buffer_inches (number)
packing_note (string)
upsell_tip (string)
fragile_confirmed (one of "none", "fragile", "extra")
</output_format>'''

system_prompt_two = """
<role>
You are a packing expert at a shipping store, not a general assistant. Your job is to estimate the smallest realistic packed dimensions for multiple different-sized items being shipped together in one box.
</role>

<rules>
Only speak in english
Do not recommend the use of packing peanuts as they are not allowed anymore. Instead recommend air pillows, bubble wrap, or paper fill.
Don't recommend anything already included with every shipment; upsells must be genuine paid add-ons. For example don't recommend buying tracking, that is already included in every UPS shipping. Do not recommend Declared Value coverage, because asking for the shipment's value is standard procedure on every shipment — it isn't an optional add-on. Keep in mind UPS services and rules.
Only recommend the following services: Ground (not guaranteed, most handling), 3 Day Select (not guaranteed, more reliable than Ground), 2nd Day Air (not guaranteed, but flies, so fewer handling touches), 2nd Day Air A.M. (guaranteed when it shows as available), and Next Day Air (all options) (guaranteed). You may not name any other services.
Never overstate a guarantee. Only 2nd Day Air A.M. and Next Day options may be described as guaranteed. All other options can be described as faster or having fewer-touches, never guaranteed.
Every lookup must get a genuine suggestion. Never opt out. Phrases like "no add-ons needed", "no upsell necessary", or similar are strictly forbidden.
Do not judge the monetary value of an item based on its description alone. Instead, condition value-related upsell tips on the value the customer declares (e.g., "If the customer declares a high value, recommend Adult Signature Required").
Base recommendations only on the information provided.

Be simple, concise, and precise.

When foldable is true and the item is not fragile, fold the item, place it in the box, and use paper fill only if there's slack. Drop tissue paper, poly bags, and garment bags entirely.

Keep packing instructions practical and specific.

Keep selling tips concise.

Estimate the smallest realistic arrangement by considering stacking, nesting, rotating, and side-by-side placement where appropriate.

Protect fragile items with realistic spacing and cushioning.

fragile_confirmed is your own assessment and may disagree with the employee's selected fragility.

If the description is too vague to confidently assess fragility, use the highest employee-provided fragility from the items instead of guessing.

Return one overall fragile_confirmed value representing the shipment. If multiple items have different fragility levels, return the highest level needed:
none < fragile < extra.

The dimensions you return MUST already include all required padding between items and around the outside of the packed group. They are FINAL packed dimensions. Python will use them directly and will NOT add additional buffer. Do not return raw object dimensions.

Your packing estimate should never provide less protection than the most fragile item would receive if it were packed by itself.
</rules>

<examples>

Input:

description:
"Grandma's ceramic vase and a small framed photo"

items:
[
  {
    "length": 20,
    "width": 8,
    "height": 8,
    "fragile": "extra",
    "foldable": false
  },
  {
    "length": 10,
    "width": 8,
    "height": 2,
    "fragile": "fragile",
    "foldable": false
  }
]

Output:
{
  "combined_length": 28,
  "combined_width": 16,
  "combined_height": 16,
  "packing_note": "Wrap the vase and frame separately with bubble wrap, keep them separated with paper cushioning, and prevent the frame from contacting the vase.",
  "upsell_tip": "If the customer declares a high value, recommend upgrading to better packing, a double-wall box, or both, along with Adult Signature Required since multiple fragile items are shipping together.",
  "fragile_confirmed": "extra"
}

</examples>

<output_format>
Return only parseable JSON. No preamble. No markdown fences.

Exactly six keys:

combined_length (number)
combined_width (number)
combined_height (number)
packing_note (string)
upsell_tip (string)
fragile_confirmed (one of "none", "fragile", "extra")
</output_format>"""


# O(1)
def sorted_dims(length, width, height):
    sd = sorted([length, width, height], reverse=True)
    return sd





# O(1)
def add_buffer(length, width, height, buffer_inches):
    new_length = length + (buffer_inches * 2)
    new_width = width + (buffer_inches * 2)
    new_height = height + (buffer_inches * 2)
    return new_length, new_width, new_height


# print(add_buffer(10,8,6,4))
# This inventory is just for testing, take out after we are done
FALLBACK_BUFFER = {
    "none": 1,
    "fragile": 2,
    "extra": 3
}
OVERLAP_INCHES = 3


# O(m log m)
def rank_boxes(new_length, new_width, new_height, inventory):
    sorted_item_dims = sorted_dims(new_length, new_width, new_height)

    fits = []
    for box in inventory:
        sorted_box_dims = sorted_dims(box["length"], box["width"], box["height"])
        if sorted_item_dims[0] <= sorted_box_dims[0] and sorted_item_dims[1] <= sorted_box_dims[1] and sorted_item_dims[
            2] <= sorted_box_dims[2]:
            volume = box['length'] * box['width'] * box['height']
            item_vol = new_length * new_width * new_height
            waste = volume - item_vol
            new_box = box.copy()
            new_box["waste"] = waste
            fits.append(new_box)
    fits.sort(key=lambda box: box["waste"])  # O(m log m)
    return fits[:3]  # O(1)


# O(1)
def stack_identical(item_amount, new_length, new_width, new_height):
    stack_multiple = min(new_length, new_width, new_height)
    if new_length == stack_multiple:
        new_length = new_length * item_amount
    elif new_width == stack_multiple:
        new_width = new_width * item_amount
    else:
        new_height = new_height * item_amount

    return new_length, new_width, new_height


# O(m^2 log m)
# item-rotation-on-a-fixed-floor is handled, box standing on alternate faces is not, that's v2 #7.
def telescoping(new_length, new_width, new_height, inventory):
    telescoped_combos = []
    possible_boxes = []
    for z in inventory:
        sorted_item_floor = sorted([new_length, new_width], reverse=True)
        sorted_box_floor = sorted([z["length"], z["width"]], reverse=True)
        if sorted_item_floor[0] <= sorted_box_floor[0] and sorted_item_floor[1] <= sorted_box_floor[1]:
            possible_boxes.append(z)
    for i in range(len(possible_boxes)):
        for j in range(i, len(possible_boxes)):
            c = possible_boxes[i]
            d = possible_boxes[j]
            combined_height = c["height"] + d["height"] - OVERLAP_INCHES
            if combined_height >= new_height:
                telescoped_combos.append({
                    "name": c["name"] + " + " + d["name"],
                    "length": min(c["length"], d["length"]),
                    "width": min(c["width"], d["width"]),
                    "height": combined_height,
                    "price": c["price"] + d["price"]
                })
    return rank_boxes(new_length, new_width, new_height, telescoped_combos)


# O(n)
def select_boxes(items, ship_together, buffer_inches, inventory, description):
    results = []

    if ship_together == False:
        for x in items:
            if x["foldable"] == True:
                bl, bw, bh = add_buffer(x["length"], x["width"], x["height"], 1)
            else:
                bl, bw, bh = add_buffer(x["length"], x["width"], x["height"], buffer_inches)
            pre_append = rank_boxes(bl, bw, bh, inventory)
            if len(pre_append) == 0:
                telescoping_attempt = telescoping(bl, bw, bh, inventory)
                if len(telescoping_attempt) == 0:
                    results.append('ERROR: NO SUITABLE BOX FOR THIS ITEM')
                else:
                    results.append(telescoping_attempt)
            else:
                results.append(pre_append)





    elif ship_together == True:
        all_same = True
        first_sorted = sorted_dims(items[0]['length'], items[0]['width'], items[0]['height'])

        for x in items:
            if (sorted_dims(x['length'], x['width'], x['height']) != first_sorted or x['foldable'] != items[0][
                'foldable'] or x['fragile'] != items[0]['fragile']):
                all_same = False
                break

        if all_same == True:
            before_pass = stack_identical(len(items), items[0]["length"], items[0]["width"], items[0]["height"])
            if items[0]["foldable"] == True:
                buffered = add_buffer(before_pass[0], before_pass[1], before_pass[2], 1)
            else:
                buffered = add_buffer(before_pass[0], before_pass[1], before_pass[2], buffer_inches)
            preappendx = rank_boxes(buffered[0], buffered[1], buffered[2], inventory)
            if len(preappendx) == 0:
                test_telescope = telescoping(buffered[0], buffered[1], buffered[2], inventory)
                if len(test_telescope) == 0:
                    results.append('ERROR: NO SUITABLE BOX FOR THIS ITEM')
                else:
                    results.append(test_telescope)


            else:
                results.append(preappendx)
        else:
            different_size_box_lookup_attempt = estimate_bounding_box(description, items)
            is_dict = isinstance(different_size_box_lookup_attempt, dict)
            if is_dict == True:
                cl = different_size_box_lookup_attempt['combined_length']
                cw = different_size_box_lookup_attempt['combined_width']
                ch = different_size_box_lookup_attempt['combined_height']
                ranked = rank_boxes(cl, cw, ch, inventory)

                if len(ranked) == 0:
                    telescope_attempt = telescoping(cl, cw, ch, inventory)
                    if len(telescope_attempt) == 0:
                        results.append('ERROR: NO BOX SUITABLE FOR THIS ITEM. ATTEMPT TO SELF MEASURE TO FIND BOX')
                    else:
                        results.append(telescope_attempt)
                else:
                    results.append(ranked)
            else:
                results.append(different_size_box_lookup_attempt)

    return results


# test foldable take out later
foldable_items = [
    {"length": 6, "width": 4, "height": 4, "foldable": True, "fragile": "none"},
]

# test stacking with all foldable take out later
stacked_foldable = [
    {"length": 6, "width": 4, "height": 4, "foldable": True, "fragile": "fragile"},
    {"length": 6, "width": 4, "height": 4, "foldable": True, "fragile": "fragile"},
    {"length": 6, "width": 4, "height": 4, "foldable": True, "fragile": "fragile"},
]

# itemsx and print statement for testing purposes
itemsx = [
    {"length": 30, "width": 30, "height": 30, "foldable": False, "fragile": "extra"}
]
itemsz2 = [
    {"length": 20, "width": 30, "height": 10, "foldable": False, "fragile": "none"},
    {"length": 30, "width": 20, "height": 10, "foldable": False, "fragile": "fragile"}
]

test_item = [{"length": 16, "width": 12, "height": 22, "foldable": False, "fragile": "none"}]

stacked_tall = [
    {"length": 16, "width": 12, "height": 7, "foldable": False, "fragile": "fragile"},
    {"length": 16, "width": 12, "height": 7, "foldable": False, "fragile": "fragile"},
    {"length": 16, "width": 12, "height": 7, "foldable": False, "fragile": "fragile"},
]


# O(1)
def parse_description(description, fragile, foldable, quantity):
    messages = []
    user_content = f'description:{description}\nfragile:{fragile}\nfoldable:{foldable}\nquantity:{quantity}'
    add_user_message(messages, user_content)

    raw = chat(messages, system=system_prompt)
    stripped_raw = strip_fences(raw)
    try:
        result = json.loads(stripped_raw)
        claude_fragility = result['fragile_confirmed']
        claude_floor = FALLBACK_BUFFER[claude_fragility]
        employee_floor = FALLBACK_BUFFER[fragile]
        chosen_buffer = max(claude_floor, employee_floor)
        if result['buffer_inches'] < chosen_buffer:
            result['buffer_inches'] = chosen_buffer

        return result

    except json.JSONDecodeError as e:
        error_json = str(e)
        print(error_json)
        fallback = {'buffer_inches': FALLBACK_BUFFER[fragile],
                    'packing_note': 'Pack the item well so it does not shake around in the box.', 'upsell_tip': '',
                    'fragile_confirmed': fragile}
        print(repr(stripped_raw))
        return fallback


def estimate_bounding_box(description, items):
    messages = []
    user_content = f'description:{description}\nitems:{json.dumps(items)}'
    add_user_message(messages, user_content)

    raw = chat(messages, system=system_prompt_two)
    stripped_raw = strip_fences(raw)
    try:
        result = json.loads(stripped_raw)
        return result

    except json.JSONDecodeError as e:
        error_json = str(e)
        print(error_json)
        fallback = 'ERROR: COULD NOT ESTIMATE COMBINED SIZE, MEASURE AND CHOOSE A BOX BY HAND'
        print(repr(stripped_raw))

        return fallback


"""
print(select_boxes(itemsz2,True, 2,INVENTORY, 'Ancient Compressed Fossilized Dinosaur Feet'))
print('------------------------')
print(parse_description("grandma's ceramic vase", "extra", False, 1))
print(parse_description("folded cotton jacket", "none", True, 1))
print(parse_description("pair of shoes in original box", "none", False, 1))
print(parse_description("stuff", "fragile", False, 1))
print('-----------------')
print(estimate_bounding_box('One broom kit and box of baseball cards ',itemsz2))
print(rank_boxes(6, 4, 3, INVENTORY))#O(1)#for testing
print(telescoping(24, 20, 28, INVENTORY))
print(select_boxes(test_item, False,1,INVENTORY, 'Grey HP Printer'))
print(select_boxes(stacked_tall, True, 1, INVENTORY,'Large Prayer Books'))
print(sorted_dims(10, 6, 4))
print(sorted_dims(4, 6, 10))
print(stack_identical(3, 5,5,6))#for testing
print(select_boxes(itemsx,True,2,INVENTORY, 'AI Server Parts'))
print(select_boxes(foldable_items, False, 3, INVENTORY, 'Grey Nike Sweatshirt'))
print(select_boxes(stacked_foldable, True, 3, INVENTORY, '3 Versace Pants'))
"""


def main():
    with open('test_inventory.csv', 'r') as handle:
        handle = handle.read()
        inventory_pre = parse_inventory(read_csv_rows(handle))
    while True:
        try:
            amount = int(input('Enter amount of items you are shipping: '))
            if amount > 0:
                break
        except ValueError:
            print('Invalid Input: Type a whole number greater than 0.')

    items = []
    while True:
        if amount > 1:
            ship_together = input('Say Yes or No to if items are being shipped together: ')
            tst_ship = ship_together.lower()

            if tst_ship == 'yes' or tst_ship == 'no':
                break
            else:
                print('Retry filling the field ship_together. Say Yes or No to if items are being shipped together:')
        else:
            ship_together = False
            break
    if amount > 1:
        if tst_ship == 'yes':
            ship_together = True
        elif tst_ship == 'no':
            ship_together = False


    fragile_number = []
    foldability = True
    box_rankings = ["BEST FIT:","2ND BEST:", "3RD BEST:"]


    for i in range(amount):


        while True:
            try:
                length = input('Enter item length: ')
                length = float(length)
                break
            except ValueError:
                print('INVALID INPUT FOR LENGTH. PLEASE ENTER A VALID NUMBER')
        while True:
            try:
                width = input('Enter item width: ')
                width = float(width)
                break
            except ValueError:
                print('INVALID INPUT FOR WIDTH. PLEASE ENTER A VALID NUMBER')
        while True:
            try:
                height = input('Enter item height: ')
                height = float(height)
                break
            except ValueError:
                print('INVALID INPUT FOR HEIGHT. PLEASE ENTER A VALID NUMBER')



        while True:
            foldable = str(input('Is the item foldable? Reply Yes or No: '))
            foldable_tst = foldable.lower()
            if foldable_tst == 'yes' or foldable_tst == 'no':
                break
            else:
                print('Retry filling in the field foldable. Reply Yes or No.')

        if foldable_tst == 'no':
            foldable = False
            foldability = False
        elif foldable_tst == 'yes':
            foldable = True


        while True:

            fragile = input('Is item fragile? Reply None, Fragile, or Extra: ')
            fragile_tst = fragile.lower()
            if fragile_tst == 'none' or fragile_tst == 'fragile' or fragile_tst == 'extra':
                break
            else:
                print('Retry filling in the field fragile. Reply None, Fragile, or Extra.')
        if fragile_tst == 'none':
            fragile = 'none'
            fragile_number.append(1)
        elif fragile_tst == 'fragile':
            fragile = 'fragile'
            fragile_number.append(2)
        elif fragile_tst == 'extra':
            fragile = 'extra'
            fragile_number.append(3)

        items.append({"length": length, "width": width, "height": height, 'foldable': foldable, 'fragile': fragile})
    description = input('Enter a description: ')

    fragile_max = max(fragile_number)
    fragile_pass = ''
    if fragile_max == 1:
        fragile_pass = 'none'
    elif fragile_max == 2:
        fragile_pass = 'fragile'
    else:
        fragile_pass = 'extra'
    description_dict = parse_description(description, fragile_pass, foldability, len(items))
    box_selection = select_boxes(items, ship_together, description_dict['buffer_inches'], inventory_pre, description)
    if description_dict['fragile_confirmed'] != fragile_pass:
        fragile_warning = f"NOTE: EMPLOYEE CHOSE FRAGILITY {fragile_pass}, BOXFIT ASSESSED {description_dict['fragile_confirmed']}"
    else:
        fragile_warning = ''
    for box_selections in box_selection:
        check = isinstance(box_selections, list)
        if check == True:
            for i, x in enumerate(box_selections):
                print(box_rankings[i],f"{x['name']} ${x['price']}")
        else:
            print(box_selections)


    print(description_dict['packing_note'])
    print(description_dict['upsell_tip'])
    print(fragile_warning)
main()