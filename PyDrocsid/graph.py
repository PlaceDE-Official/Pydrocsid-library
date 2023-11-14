class Graph:
    def __init__(self) -> None:
        self._connections = dict()
        self._vertices = set()

    @classmethod
    def from_tuples(cls, data: list[tuple]):
        graph = Graph()
        for u, v in data:
            graph.add_edge(u, v)
        return graph

    def add_edge(self, u, v) -> None:
        self._connections.setdefault(u, []).append(v)
        self._vertices.add(u)
        self._vertices.add(v)

    def is_cyclic_recursion(self, u, visited, stack) -> bool:
        visited[u] = True
        stack[u] = True

        # Recur for all neighbours
        # if any neighbour is visited and in
        # stack then graph is cyclic
        for neighbour in self._connections.get(u, []):
            if not visited[neighbour]:
                if self.is_cyclic_recursion(neighbour, visited, stack):
                    return True
            elif stack[neighbour]:
                return True

        stack[u] = False
        return False

    def is_cyclic(self) -> bool:
        visited = {connection: False for connection in self._vertices}
        stack = {connection: False for connection in self._vertices}
        for node in self._connections:
            if not visited[node]:
                if self.is_cyclic_recursion(node, visited, stack):
                    return True
        return False
