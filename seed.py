from sqlalchemy.orm import Session
from db import db
from sqlalchemy import select
from inventory_parser import parse_inventory, read_csv_rows
from models import Store, Box
from sqlalchemy import delete
with Session(db) as session:
    #item = Store(name="THE UPS STORE", store_number="5898")
    #session.add(item)
    #session.commit()
    store_info = select(Store)
    for x in session.scalars(store_info):
        print(x.name, x.store_number)
    store_object = session.scalars(store_info).first()
    store_id = store_object.id
    idc = delete(Box).where(Box.store_id == store_id )
    session.execute(idc)
    with open('test_inventory.csv', 'r') as t:
        inventory_text = t.read()
        inventext = read_csv_rows(inventory_text)
        inventory_dict = parse_inventory(inventext)
        for i in range(len(inventory_dict)):
            item = Box(store_id=store_id, box_name=inventory_dict[i]['box_name'],length=inventory_dict[i]['length'],width=inventory_dict[i]['width'],height=inventory_dict[i]['height'],wall_type=inventory_dict[i]['wall_type'],box_only_price=inventory_dict[i]['price'],std_pack_price=inventory_dict[i]['standard_packing_price'],frag_pack_price=inventory_dict[i]['fragile_packing_price'])
            session.add(item)

        session.commit()