"""Canonical expert-tag sets; -1 is missing metadata, never a named skill."""


def parse_tags(value):
    tags = {int(t.strip()) for t in str(value).split(";")}
    if any(t < -1 for t in tags):
        raise ValueError("Tag IDs must be nonnegative or -1 (unknown)")
    tags.discard(-1)
    return tuple(sorted(tags)) if tags else (-1,)


def tag_mapping(values):
    tags = {-1}
    for value in values:
        tags.update(parse_tags(value))
    return {str(t):i for i,t in enumerate(sorted(tags))}


def tag_indices(value, mapping):
    return tuple(mapping[str(t)] for t in parse_tags(value))
