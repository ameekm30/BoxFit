from sqlalchemy.orm import Session
from sqlalchemy import select
from db import db
from models import Box
def retrive_inventory(store_id):
    with Session(db) as session:
        store_info = select(Box)
        store_info = store_info.where(Box.store_id == store_id)
        store_object = session.scalars(store_info)
        thing_of_dicts = []
        for x in store_object:
            if int(x.length) == x.length:
                length = int(x.length)
            else:
                length = x.length
            if int(x.width) == x.width:
                width = int(x.width)
            else:
                width = x.width
            if int(x.height) == x.height:
                height = int(x.height)
            else:
                height = x.height
            if len(x.box_name) == 0:
                box_name = ''
            else:
                box_name = x.box_name + ' '
            name = box_name + str(length) + 'x' + str(width) + 'x' + str(height) + ' ' + x.wall_type
            box_dict = {"box_name": x.box_name, "name": name, "length": x.length, "width": x.width, "height": x.height, "price": x.box_only_price, "wall_type": x.wall_type, 'standard_packing_price': x.std_pack_price,'fragile_packing_price': x.frag_pack_price}
            thing_of_dicts.append(box_dict)
        return thing_of_dicts

#print(retrive_inventory(1))
