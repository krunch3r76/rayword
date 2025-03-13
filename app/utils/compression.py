# util/compression.py


def decompress_json(compressed_text):
    import gzip
    import base64
    import json

    from_base64 = True
    if not isinstance(compressed_text, str):
        from_base64 = False

    if not from_base64:
        # Decompress compressed bytes
        text_bytes = gzip.decompress(compressed_text)
    else:
        # Convert string to bytes
        base64_bytes = compressed_text.encode("utf-8")

        # Decode from base64
        compressed_bytes = base64.b64decode(base64_bytes)

        # Decompress
        text_bytes = gzip.decompress(compressed_bytes)

    # Convert bytes back to string
    text = text_bytes.decode("utf-8")

    as_object = json.loads(text)
    return as_object
