import timeit
import sys

class MockVector:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    @property
    def co(self):
        return self

class MockMatrix:
    def __matmul__(self, other):
        # Simulate some work
        return MockVector(other.x, other.y, other.z)

class MockVertices:
    def __init__(self, num_verts):
        self._verts = [MockVector(i, i, i) for i in range(num_verts)]

    def __iter__(self):
        return iter(self._verts)

    def __len__(self):
        return len(self._verts)

    def __getitem__(self, index):
        return self._verts[index]

class MockData:
    def __init__(self, num_verts):
        self.vertices = MockVertices(num_verts)

class MockObject:
    def __init__(self, num_verts):
        self.data = MockData(num_verts)
        self.matrix_world = MockMatrix()

def current_way(low_obj):
    # Original code (what it was before my change)
    verts = list(low_obj.data.vertices)
    if verts:
        mw = low_obj.matrix_world
        bottom_z = min((mw @ v.co).z for v in verts)
        return bottom_z

def optimized_way(low_obj):
    # My optimized code
    verts = low_obj.data.vertices
    if len(verts) > 0:
        mw = low_obj.matrix_world
        bottom_z = min((mw @ v.co).z for v in verts)
        return bottom_z

if __name__ == "__main__":
    num_verts = 1000000
    low_obj = MockObject(num_verts)

    # Warm up
    current_way(low_obj)
    optimized_way(low_obj)

    iterations = 20

    t1 = timeit.timeit(lambda: current_way(low_obj), number=iterations)
    t2 = timeit.timeit(lambda: optimized_way(low_obj), number=iterations)

    print(f"Current way (1M verts): {t1:.4f}s")
    print(f"Optimized way (1M verts): {t2:.4f}s")
    print(f"Improvement: {(t1 - t2) / t1 * 100:.2f}%")

    import gc
    gc.collect()

    import sys
    test_list = list(range(num_verts))
    print(f"Memory overhead of list of {num_verts} elements: {sys.getsizeof(test_list) / 1024 / 1024:.2f} MB")
