
import collections

def nodups(lst):
    return list(collections.OrderedDict.fromkeys(lst))


