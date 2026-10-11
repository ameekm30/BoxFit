import base64
import io
import openpyxl
import json
import csv
from chat_helpers import chat, add_user_message, add_assistant_message, strip_fences
"""
with open('test_inventory.csv', 'r') as t:
    inventory_text = t.read()
with open('boxes.xlsx', 'rb') as f:
    excel_bytes = f.read()
"""

system_prompt_three = """
<role>
You are a data extraction expert at a shipping store, not a general assistant. Your job is to accurately read and digitize a box price sheet.
</role>
<rules>
Only speak in english.
Read the sheet row by row, not column by column. Process and state each row's size label along with its own prices before moving to the next row to prevent data skewing.
If the wall type is missing or not explicitly stated on the sheet for a box, always default to Single Wall and output "SW".
If a price cell says "Add Manually" or is completely blank, look for a handwritten price. If there is a readable handwritten number, use it. If the space is genuinely blank or only says "Add Manually", output the exact string "Add Manually (Employee's call)".
Only output null if there is printed text or handwriting present in a cell, but it is completely illegible (e.g., due to a smudge, scratch, or glare). Do not guess or hallucinate numbers.
All dimensions must be extracted as numbers. Remove any dollar signs or text from price values so they are purely numerical. (The only exception is the string "Add Manually (Employee's call)").
</rules>
<examples>
Input:
BOX SIZE          WALL   BOX ONLY     STANDARD PACKING    FRAGILE PACKING
10 X 10 X 10      SW     $5.99        $14.99              $16.99
12 X 12 X 6       SW     $7.99        11.99               $16.99
24 X 24 X 24      SW     $22.99       $59.99              $79.99
24 X 24 X 24      DW     $48.99       Add Manually        Add Manually
Output:
[
  {
    "length": 10,
    "width": 10,
    "height": 10,
    "wall_type": "SW",
    "price_box_only": 5.99,
    "price_standard_packing": 14.99,
    "price_fragile_packing": 16.99
  },
  {
    "length": 12,
    "width": 12,
    "height": 6,
    "wall_type": "SW",
    "price_box_only": 7.99,
    "price_standard_packing": 11.99,
    "price_fragile_packing": 16.99
  },
  {
    "length": 24,
    "width": 24,
    "height": 24,
    "wall_type": "SW",
    "price_box_only": 22.99,
    "price_standard_packing": 59.99,
    "price_fragile_packing": 79.99
  },
  {
    "length": 24,
    "width": 24,
    "height": 24,
    "wall_type": "DW",
    "price_box_only": 48.99,
    "price_standard_packing": "Add Manually (Employee's call)",
    "price_fragile_packing": "Add Manually (Employee's call)"
  }
]
</examples>
<output_format>
Return only parseable JSON. No preamble. No markdown fences.
Return a JSON array (list) of objects, starting with [ and ending with ].
Each object in the array must contain exactly seven keys:
length (number or null)
width (number or null)
height (number or null)
wall_type (string, e.g., "SW" or "DW")
price_box_only (number or string)
price_standard_packing (number or string)
price_fragile_packing (number or string)
</output_format>
"""
system_prompt_four ="""<role>
Identify which column contains each required field in a shipping store's price sheet.
</role>

<rules>
- Column positions start at 0.
- Match columns by their header meaning, allowing reasonable variations in wording.
- Return the position of each required field.
- If a required field has no corresponding column in the file, return null.
- Do not guess when a field is genuinely absent.
</rules>

<fields>
- box_name
- box_size
- wall_type
- box_only_price
- standard_packing_price
- fragile_packing_price
</fields>

<output_format>
Return only parseable JSON. No preamble. No markdown fences.
Return exactly these six integer keys:
{
  "box_name": <integer or null>,
  "box_size": <integer or null>,
  "wall_type": <integer or null>,
  "box_only_price": <integer or null>,
  "standard_packing_price": <integer or null>,
  "fragile_packing_price": <integer or null>
}
</output_format>
"""
system_prompt_five="""
<role>
Map a list of raw wall-type strings from a shipping store's price sheet to standard designations: "SW", "DW", "TW", or "UNKNOWN".
</role>

<rules>
- English only.
- You will receive a JSON list of raw strings found in the wall-type column of a price sheet.
- For each string, determine if it represents Single Wall ("SW"), Double Wall ("DW"), or Triple Wall ("TW").
- If the string does not clearly indicate one of these three wall counts (e.g., if it indicates a board grade like "ECT-32", marketing terms like "Heavy Duty", or is completely unrelated), you MUST map it to "UNKNOWN". Do not guess or hallucinate a wall count based on board grade or box strength.
- The keys in your output JSON must be the EXACT strings provided in the input list, preserving all original casing, spacing, and punctuation. If you alter a key, the lookup will fail.
- The values must be ONLY "SW", "DW", "TW", or "UNKNOWN".
</rules>

<examples>
Input:
["SINGLE WALL", "D/W", "ECT-32", "TRIPLE", "Heavy Duty", "S.W."]

Output:
{
  "SINGLE WALL": "SW",
  "D/W": "DW",
  "ECT-32": "UNKNOWN",
  "TRIPLE": "TW",
  "Heavy Duty": "UNKNOWN",
  "S.W.": "SW"
}
</examples>

<output_format>
Return only parseable JSON. No preamble. No markdown fences.
Return a single JSON object where the keys are the exact input strings and the values are "SW", "DW", "TW", or "UNKNOWN".
</output_format>
"""
#O(n*l) where n = number of lines in the csv and where l = average length of each line.
def read_csv_rows(csv_text):
    csv_result = []
    all_lines = csv_text.split('\n')
    for row in csv.reader(all_lines):
        if len(row) == 0:
            continue

        csv_result.append(row)
    return csv_result

def read_excel_rows(excel_bytes):
    pre = []
    workbook = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    sheet = workbook.active

    for row in sheet.iter_rows(values_only=True):
        list_tup = []

        for string in row:
            if string == None:
                string = ''
            string = str(string)
            list_tup.append(string)
        if list_tup.count('') == len(list_tup):
            continue
        pre.append(list_tup)
    return pre

def wall_type_helper(wall_type):
    if (len(wall_type) == 0) or (wall_type == 'SW') or (wall_type == 'S/W') or (wall_type == 'SINGLE') or (
            wall_type == 'SINGLE WALL'):
        return 'SW'
    elif (wall_type == "DW") or (wall_type == "D/W") or (wall_type == "DOUBLE WALL") or (wall_type == "DOUBLE"):
        return 'DW'
    elif (wall_type == "TW") or (wall_type == "T/W") or (wall_type == "TRIPLE WALL") or (wall_type == "TRIPLE"):
        return 'TW'
    else:
       return None










#O(n*l) where n = number of lines in the text and where l = average length of each line. Note: The cost is one network round trip, which Big-O hides.
def parse_inventory(text_rows):
    messages = []
    header = None
    for index, row in enumerate(text_rows):
        non_empty_cells = len(row) - row.count('')
        if non_empty_cells >= 2:
            header = index
            break
    if header == None:
        return 'ERROR: COULD NOT USE INVENTORY PROVIDED (NO HEADER ROW)'

    joined = ','.join(text_rows[header])
    all_lines = text_rows[header + 1:]
    add_user_message(messages, joined)
    output2 = chat(messages, system=system_prompt_four, stop_sequences=[])
    strip_output2 = strip_fences(output2)
    inventory_result = []
    non_fits = []
    column_map = json.loads(strip_output2)
    if column_map['box_size'] == None:
        return 'ERROR: THE INVENTORY PROVIDED HAS NO BOX SIZES PROVIDED. PLEASE PROVIDE AN INVENTORY WITH BOX SIZES TO CONTINUE.'

    for parts in all_lines:
        if column_map['box_size'] !=  None:
            box_size_start = parts[column_map['box_size']]
            box_parts = box_size_start.lower().split('x')
            length = float(box_parts[0])
            width = float(box_parts[1])
            height = float(box_parts[2])
        else:
            continue
        if column_map['wall_type']!=  None:
            wall_type = parts[column_map['wall_type']].strip().upper()
            wall_type2 = wall_type_helper(wall_type)
            if wall_type2 == None:
                non_fits.append(wall_type)
    #print(non_fits)
    if len(non_fits) > 0:
        raw = json.dumps(non_fits)
        add_user_message(messages,raw)
        pre_wall_map = chat(messages, system_prompt_five, stop_sequences=[])
        prepre = strip_fences(pre_wall_map)
        wall_map = json.loads(prepre)
    else:
        wall_map = {}

    for parts in all_lines:

        if column_map['box_name'] != None:
            box_name = parts[column_map['box_name']].strip()
            if len(box_name) == 0:
                box_name = ''
            else:
                box_name = box_name + ' '
        else:
            box_name = ''
        if column_map['box_size'] !=  None:
            box_size_start = parts[column_map['box_size']]
            box_parts = box_size_start.lower().split('x')
            length = float(box_parts[0])
            width = float(box_parts[1])
            height = float(box_parts[2])
        else:
            continue
        if column_map['wall_type'] !=  None:
            wall_type = parts[column_map['wall_type']].strip().upper()
            wall_type3 = wall_type_helper(wall_type)
            if wall_type3 is not None:
                wall_type = wall_type3
            else:
                if wall_type in wall_map:
                    wall_type = wall_map[wall_type]
                else:
                    wall_type = 'UNKNOWN'
        else:
            wall_type = 'SW'




        if column_map['box_only_price'] !=  None:
            boxpricestart = parts[column_map['box_only_price']]
            fbp = boxpricestart.strip('$').replace(',','')

            try:
                box_only_price = float(fbp)
            except ValueError:
                box_only_price = None
        else:
            box_only_price = None
        if column_map['standard_packing_price'] !=  None:
            boxpricestarttwo = parts[column_map['standard_packing_price']]
            fbp2 = boxpricestarttwo.strip('$').replace(',','')
            try:
                standard_packing_price = float(fbp2)
            except ValueError:
                standard_packing_price = None
        else:
            standard_packing_price = None

        if column_map['fragile_packing_price'] !=  None:
            boxpricestartthree = parts[column_map['fragile_packing_price']]
            fbp3 = boxpricestartthree.strip('$').replace(',','')
            try:
                fragile_packing_price = float(fbp3)
            except ValueError:
                fragile_packing_price = None
        else:
            fragile_packing_price = None
        #print(length, width, height, wall_type, box_only_price,standard_packing_price,fragile_packing_price)

        pre_length = int(length)
        pre_width = int(width)
        pre_height = int(height)
        if  pre_length != length:
            pre_length = length

        if pre_height != height:
            pre_height = height

        if pre_width != width:
            pre_width = width

        name = str(box_name) +  str(pre_length) + 'x' + str(pre_width) + 'x' + str(pre_height) + ' ' +  wall_type

        pre_inventory_dict = {"name": name, "length": length, "width": width, "height": height, "price": box_only_price, "wall_type": wall_type, 'standard_packing_price': standard_packing_price,'fragile_packing_price': fragile_packing_price}

        inventory_result.append(pre_inventory_dict)
    return inventory_result




'''
print(column_map)
with open('tst.png', 'rb') as f:
    raw_bytes = f.read()
encoded = base64.b64encode(raw_bytes)
encoded_string = encoded.decode('utf-8')
image_block = {
    "type": "image",
    "source": {
        "type": "base64",
        "media_type": "image/png",
        "data": encoded_string
    }
}

text_block = {"type": "text", "text": "Box price sheet from shipping store."}
content = [image_block, text_block]
add_user_message(messages, content)
output = chat(messages, system=system_prompt_three, stop_sequences=[])
print(repr(output))
strip_output = strip_fences(output)
jsond = json.loads(strip_output)
print(jsond)
'''

#print(read_csv_rows(inventory_text))
#print(parse_inventory(read_csv_rows(inventory_text)))
#print(parse_inventory(read_excel_rows(excel_bytes)))
#print(parse_inventory(read_csv_rows(inventory_text)))
