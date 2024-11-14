import collections

def infinite_defaultdict():
    '''A bottomless defaultdict.''' 
    return collections.defaultdict(infinite_defaultdict)
