def merge_dicts(*dict_args):
    """ Merges any number of ``dict``s.

    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.

    :param dict_args:  The ``dict``s to be merged.
    :return dict: The merged ``dict``.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result
