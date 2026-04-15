GLOBAL_CONTEXT = None


def set_memory(data):
    global GLOBAL_CONTEXT
    GLOBAL_CONTEXT = data


def get_memory():
    return GLOBAL_CONTEXT