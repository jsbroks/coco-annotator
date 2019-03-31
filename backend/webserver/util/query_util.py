import json


def fix_ids(objs):
    objects_list = json.loads(objs.to_json().replace('\"_id\"', '\"id\"'))
    return objects_list

