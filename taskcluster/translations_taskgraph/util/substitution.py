class PartialSubstitutionDict(dict):
    """A dictionary that will return any missing keys as their formatable
    version. Useful when a string needs to be formatted multiple times
    in different places to get to its final form."""

    def __missing__(self, key):
        return "{" + key + "}"


def substitute(item, **subs):
    if isinstance(item, list):
        for i in range(len(item)):
            item[i] = substitute(item[i], **subs)
    elif isinstance(item, dict):
        new_dict = {}
        for k, v in item.items():
            k = k.format_map(PartialSubstitutionDict(subs))
            new_dict[k] = substitute(v, **subs)
        item = new_dict
    elif isinstance(item, str):
        item = item.format_map(PartialSubstitutionDict(subs))
    else:
        item = item

    return item
