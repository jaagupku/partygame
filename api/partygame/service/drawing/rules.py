"""Deterministic assignment and integer point allocation, without I/O."""

from random import Random


def assignments(count: int, seed: int) -> tuple[list[int], list[list[int]]]:
    if count < 3:
        raise ValueError("needs_three_players")
    random = Random(seed)
    criteria = list(range(count))
    for _ in range(100):
        random.shuffle(criteria)
        if all(topic != owner for topic, owner in enumerate(criteria)):
            break
    else:
        criteria = list(range(1, count)) + [0]
    edges = {
        topic: [p for p in range(count) if p != topic and (count == 3 or p != criteria[topic])]
        for topic in range(count)
    }
    result: list[list[int]] = [[] for _ in range(count)]
    matched: dict[int, int] = {}
    for _ in range(2 if count <= 4 else 3):
        matched.clear()

        def augment(topic: int, seen: set[int]) -> bool:
            for player in edges[topic]:
                if player in seen:
                    continue
                seen.add(player)
                if player not in matched or augment(matched[player], seen):
                    matched[player] = topic
                    return True
            return False

        topics = list(range(count))
        random.shuffle(topics)
        for neighbors in edges.values():
            random.shuffle(neighbors)
        for topic in topics:
            if not augment(topic, set()):
                raise RuntimeError("Unbalanced drawing assignment")
        for player, topic in matched.items():
            result[topic].append(player)
            edges[topic].remove(player)
    return criteria, result


def allocate_points(votes: list[int]) -> tuple[list[int], str]:
    """Input order is the persisted random drawing order, including tie breaks."""
    if not votes:
        return [], "empty"
    if len(votes) == 1:
        return [1000], "uncontested"
    weights = votes if sum(votes) else [1] * len(votes)
    total = sum(weights)
    points = [1000 * weight // total for weight in weights]
    order = sorted(range(len(votes)), key=lambda i: -(1000 * weights[i] % total))
    for index in order[: 1000 - sum(points)]:
        points[index] += 1
    return points, "votes" if sum(votes) else "no_votes"
