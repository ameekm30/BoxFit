import streamlit as st
import pandas as pd
from box_fit_algorithm import select_boxes, parse_description
from inventory_parser import parse_inventory, read_csv_rows

st.title("BoxFit")


@st.cache_data
def load_inventory():
    with open("test_inventory.csv", "r") as f:
        return parse_inventory(read_csv_rows(f.read()))


inventory = load_inventory()

starting_rows = pd.DataFrame(
    [{"length": 10.0, "width": 8.0, "height": 6.0, "foldable": False, "fragile": "none"}]
)
table = st.data_editor(
    starting_rows,
    num_rows="dynamic",
    column_config={
        "length": st.column_config.NumberColumn("Length (in)", min_value=0.1, required=True),
        "width": st.column_config.NumberColumn("Width (in)", min_value=0.1, required=True),
        "height": st.column_config.NumberColumn("Height (in)", min_value=0.1, required=True),
        "foldable": st.column_config.CheckboxColumn("Foldable", default=False),
        "fragile": st.column_config.SelectboxColumn(
            "Fragile", options=["none", "fragile", "extra"], default="none", required=True
        ),
    },
)
ship_together = st.checkbox("Ship all items together in one box")
description = st.text_input("Describe the item(s)")

if st.button("Find box"):
    if table.isnull().values.any() or len(table) == 0 or description.strip() == "":
        st.error("Fill in every cell and add a description.")
        st.stop()
    items = table.to_dict("records")
    box_rankings = ["BEST FIT:", "2ND BEST:", "3RD BEST:"]
    fragile_number = []
    foldability = True


    for item in items:

        if item["foldable"] == False:
            foldability = False
        if item['fragile'] == 'none':
            fragile_number.append(1)
        elif item['fragile'] == 'fragile':
            fragile_number.append(2)
        else:
            fragile_number.append(3)
    fragile_max = max(fragile_number)
    fragile_pass = ''
    if fragile_max == 1:
        fragile_pass = 'none'
    elif fragile_max == 2:
        fragile_pass = 'fragile'
    else:
        fragile_pass = 'extra'

    with st.spinner("Finding the best box..."):
        description_dict = parse_description(description, fragile_pass, foldability, len(items))
        box_selection = select_boxes(items, ship_together, description_dict['buffer_inches'], inventory,description)
        if description_dict['fragile_confirmed'] != fragile_pass:
            fragile_warning = f"NOTE: EMPLOYEE CHOSE FRAGILITY {fragile_pass}, BOXFIT ASSESSED {description_dict['fragile_confirmed']}"
        else:
            fragile_warning = ''
        for box_selections in box_selection:
            check = isinstance(box_selections, list)
            if check == True:
                for i, x in enumerate(box_selections):
                    st.write(box_rankings[i], f"{x['name']} ${x['price']}")
            else:
                st.write(box_selections)

        st.write(description_dict['packing_note'])
        st.write(description_dict['upsell_tip'])
        st.write(fragile_warning)
