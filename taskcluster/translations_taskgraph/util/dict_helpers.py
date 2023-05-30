def deep_get(dict_, field):
    container, subfield = dict_, field
    while "." in subfield:
        f, subfield = subfield.split(".", 1)
        if f not in container:
            return None

        container = container[f]

    return container.get(subfield)
