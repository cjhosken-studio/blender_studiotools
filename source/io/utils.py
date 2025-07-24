def get_all_objects_from_collection(collection, include_children=True):
    objects = []
    objects.extend(collection.objects)
    if include_children:
        for child_collection in collection.children:
            objects.extend(get_all_objects_from_collection(child_collection, include_children=True))
    return objects