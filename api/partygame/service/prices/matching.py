"""Maximum cardinality matching for the undirected product-comparison graph.

Blossom contraction handles odd cycles (three products can all be comparable).
Greedy pairing can incorrectly report insufficient content, e.g. 10, 11, 29, 30.
"""

from collections import deque


def maximum_pairs(graph: list[list[int]]) -> list[tuple[int, int]]:
    size = len(graph)
    match = [-1] * size

    def augment(root):
        parent = [-1] * size
        base = list(range(size))
        used = [False] * size
        queue = deque([root])
        used[root] = True

        def ancestor(left, right):
            path = set()
            while True:
                left = base[left]
                path.add(left)
                if match[left] == -1:
                    break
                left = parent[match[left]]
            while base[right] not in path:
                right = parent[match[base[right]]]
            return base[right]

        def mark(vertex, common, child, blossom):
            while base[vertex] != common:
                blossom.add(base[vertex])
                blossom.add(base[match[vertex]])
                parent[vertex] = child
                child = match[vertex]
                vertex = parent[match[vertex]]

        while queue:
            vertex = queue.popleft()
            for target in graph[vertex]:
                if base[vertex] == base[target] or match[vertex] == target:
                    continue
                if target == root or (match[target] != -1 and parent[match[target]] != -1):
                    common = ancestor(vertex, target)
                    blossom = set()
                    mark(vertex, common, target, blossom)
                    mark(target, common, vertex, blossom)
                    for index in range(size):
                        if base[index] in blossom:
                            base[index] = common
                            if not used[index]:
                                used[index] = True
                                queue.append(index)
                elif parent[target] == -1:
                    parent[target] = vertex
                    if match[target] == -1:
                        while target != -1:
                            previous = parent[target]
                            next_target = match[previous] if previous != -1 else -1
                            match[target] = previous
                            if previous != -1:
                                match[previous] = target
                            target = next_target
                        return
                    partner = match[target]
                    used[partner] = True
                    queue.append(partner)

    for index in range(size):
        if match[index] == -1:
            augment(index)
    return [(index, partner) for index, partner in enumerate(match) if partner > index]
