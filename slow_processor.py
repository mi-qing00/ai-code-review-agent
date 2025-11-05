"""
Data processing module with intentional performance issues for demo purposes.
This code demonstrates performance problems that AI code review can detect.
"""


def find_duplicates(items):
    """
    Find duplicate items - O(n²) complexity.
    
    ⚠️ PERFORMANCE ISSUE: Inefficient nested loop
    """
    duplicates = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] == items[j]:
                duplicates.append(items[i])
    return duplicates
    # Should use set() for O(n) complexity: return list(set(items))


def process_data(data):
    """
    Process data with inefficient membership check.
    
    ⚠️ PERFORMANCE ISSUE: list membership check is O(n)
    """
    result = []
    for item in data:
        if item not in result:  # O(n) operation inside loop = O(n²)
            result.append(item)
    return result
    # Should use set: result = list(dict.fromkeys(data))


def search_items(items, target):
    """
    Linear search in unsorted list.
    
    ⚠️ PERFORMANCE ISSUE: Should use binary search or hash table
    """
    for item in items:
        if item == target:
            return True
    return False
    # For sorted list: use bisect.bisect_left()
    # For unsorted: use set for O(1) lookup


def concatenate_strings(strings):
    """
    String concatenation in loop.
    
    ⚠️ PERFORMANCE ISSUE: String concatenation creates new objects
    """
    result = ""
    for s in strings:
        result += s  # Creates new string object each time
    return result
    # Should use: "".join(strings)
