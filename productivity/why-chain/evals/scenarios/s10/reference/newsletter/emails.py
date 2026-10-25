def normalize(address):
    return address.strip().lower()


def is_valid(address):
    local, at, domain = address.partition("@")
    return bool(local) and bool(at) and "." in domain
