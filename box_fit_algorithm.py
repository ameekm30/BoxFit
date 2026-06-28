# Overall time complexity is O(n) where n = number of items being shipped
#O(1)
def add_buffer(length, width, height, buffer_inches):
    new_length = length + (buffer_inches * 2)
    new_width = width + (buffer_inches * 2)
    new_height = height + (buffer_inches * 2)
    return new_length, new_width, new_height
#print(add_buffer(10,8,6,4))
#This inventory is just for testing, take out after we are done

INVENTORY = [
    {"name": "Small",  "length": 8,  "width": 6,  "height": 4,  "price": 1.50},
    {"name": "Medium", "length": 12, "width": 10, "height": 8,  "price": 2.50},
    {"name": "Large",  "length": 18, "width": 14, "height": 12, "price": 4.00},
    {"name": "XLarge", "length": 24, "width": 20, "height": 16, "price": 6.00},
]
#O(nlogn)
def rank_boxes(new_length ,new_width,new_height, inventory):
    fits = []
    for box in inventory:
        if new_length <= box["length"] and new_width <= box["width"] and new_height <= box["height"]:

            volume = box['length'] * box['width'] * box['height']
            item_vol = new_length * new_width * new_height
            waste = volume - item_vol
            new_box = box.copy()
            new_box["waste"] = waste
            fits.append(new_box)
    fits.sort(key=lambda box: box["waste"])#O(nlogn)
    return fits[:3]#O(1)

print(rank_boxes(6, 4, 3, INVENTORY))#O(1)#for testing

#O(1)
def stack_identical(item_amount, new_length, new_width, new_height):
    stack_multiple = min(new_length, new_width, new_height)
    if new_length == stack_multiple:
        new_length = new_length * item_amount
    elif new_width == stack_multiple:
        new_width = new_width * item_amount
    else:
        new_height = new_height * item_amount

    return new_length, new_width, new_height
print(stack_identical(3, 5,5,6))#for testing
#O(n)
def select_boxes(items,ship_together,buffer_inches,inventory):
    results =[]

    if ship_together == False:
        for x in items:
            if x["foldable"] == True:
                bl, bw, bh = add_buffer(x["length"], x["width"], x["height"], 1)
            else:
                bl, bw, bh = add_buffer(x["length"], x["width"], x["height"], buffer_inches)
            pre_append = rank_boxes(bl, bw, bh, inventory)
            if len(pre_append) == 0:
                results.append('ERROR: NO SUITABLE BOX FOR THIS ITEM')
            else:
                results.append(pre_append)
    elif ship_together == True:
        all_same = True
        for x in items:
            if x != items[0]:
                all_same = False
                break
        if all_same == True:
            before_pass = stack_identical(len(items), items[0]["length"],items[0]["width"],items[0]["height"])
            if items[0]["foldable"] == True:
                buffered = add_buffer(before_pass[0], before_pass[1], before_pass[2], 1)
            else:
                buffered = add_buffer(before_pass[0], before_pass[1], before_pass[2], buffer_inches)
            preappendx = rank_boxes(buffered[0], buffered[1], buffered[2], inventory)
            if len(preappendx) == 0:
                results.append('ERROR: NO SUITABLE BOX FOR THIS ITEM')
            else:
                results.append(preappendx)
        else:
            results.append('DIFFERENT SIZE ITEMS - REQUIRES CLAUDE CALL')


    return results

# test foldable take out later
foldable_items = [
    {"length": 6, "width": 4, "height": 4, "foldable": True},
]
print(select_boxes(foldable_items, False, 3, INVENTORY))

# test stacking with all foldable take out later
stacked_foldable = [
    {"length": 6, "width": 4, "height": 4, "foldable": True},
    {"length": 6, "width": 4, "height": 4, "foldable": True},
    {"length": 6, "width": 4, "height": 4, "foldable": True},
]
print(select_boxes(stacked_foldable, True, 3, INVENTORY))
#itemsx and print statement for testing purposes
itemsx = [
{"length": 30, "width": 30, "height": 30, "foldable": False}
]
itemsz2 = [
{"length": 20, "width": 30, "height": 10, "foldable": False},
{"length": 30, "width": 20, "height": 10, "foldable": False}
]
print(select_boxes(itemsx,True,2,INVENTORY))
print(select_boxes(itemsz2,True,2,INVENTORY))
