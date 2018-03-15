def headers_to_dict(header_file):
    """Reads from a header file and generates a ``dict`` from it.

    :param str header_file: Path to the header file.
    :return dict: The headers, in a ``dict`` representation.
    """
    headers_dict = {}
    with open(header_file, 'r') as headers:
        for header in headers:
            key, value = header.split(': ', 1)
            if key in headers_dict:
                raise KeyError('key {} is present twice in header file {}'.format(key, header_file))
            headers_dict[key] = value
    return headers_dict
