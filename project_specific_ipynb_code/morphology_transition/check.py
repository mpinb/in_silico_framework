
from neuron import h

def build_section_graph():
    """
    Returns a dictionary where:
        graph[sec_name] = [list of child section names]
    """
    graph = {}
    for sec in h.allsec():
        parent_name = sec.name()
        graph[parent_name] = []
        # sec.children() returns an iterator of child sections connected to sec
        for child_sec in sec.children():
            graph[parent_name].append(child_sec.name())
    return graph

def has_cycle(graph):
    """
    Returns True if a cycle is found in 'graph', otherwise False.
    'graph' should be a dict: node -> list of children (strings)
    """
    visited = set()
    stack = set()

    def dfs(node):
        visited.add(node)
        stack.add(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in stack:
                # We found a node already on the recursion stack -> cycle
                return True
        stack.remove(node)
        return False

    # Try DFS from each node not yet visited
    for node in graph:
        if node not in visited:
            if dfs(node):
                return True
    return False

from neuron import h

# Build the graph
g = build_section_graph()

# Check for cycles
if has_cycle(g):
    print("A cycle (loop) was detected in your topology!")
else:
    print("No cycles found in your topology.")

def find_first_cycle(graph):
    """
    Detects the first cycle in the directed graph (if any) and returns
    a list of section names that form that cycle. If no cycle is found,
    returns None.
    """
    visited = set()   # set of nodes that have been fully explored
    stack = []        # current path of DFS (acting like a recursion stack)
    in_stack = set()  # set for quick membership checks of nodes in stack

    def dfs(node):
        visited.add(node)
        stack.append(node)
        in_stack.add(node)

        for neighbor in graph[node]:
            if neighbor not in visited:
                # Explore neighbor
                cycle = dfs(neighbor)
                if cycle:
                    return cycle
            elif neighbor in in_stack:
                # We've encountered a node that is already on the current path:
                # => We found a cycle. Extract it from 'stack'.
                idx = stack.index(neighbor)
                cycle_path = stack[idx:]  # sub-list from the first occurrence of 'neighbor' to the end
                return cycle_path

        # Done exploring this node
        stack.pop()
        in_stack.remove(node)
        return None

    # Run DFS from each node that hasn't been visited yet
    for node in graph:
        if node not in visited:
            cycle = dfs(node)
            if cycle:
                return cycle

    return None  # No cycle found
