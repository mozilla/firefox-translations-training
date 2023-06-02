def substitute(item, **subs):
    if isinstance(item, list):
        for i in range(len(item)):
            item[i] = substitute(item[i], **subs)
    elif isinstance(item, dict):
        new_dict = {}
        for k, v in item.items():
            k = k.format(**subs)
            new_dict[k] = substitute(v, **subs)
        item = new_dict
    elif isinstance(item, str):
        item = item.format(**subs)
    else:
        item = item

    return item
