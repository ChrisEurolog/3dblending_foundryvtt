import timeit

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

class MockData:
    def __init__(self, num_verts):
        self.vertices = [MockVector(i, i, i) for i in range(num_verts)]

class MockObject:
    def __init__(self, num_verts):
        self.data = MockData(num_verts)
        self.matrix_world = MockMatrix()

def original_way(low_obj):
    # This is what it was before
    verts = list(low_obj.data.vertices)
    if verts:
        bottom_z = min((low_obj.matrix_world @ v.co).z for v in verts)
        return bottom_z

def optimized_way(low_obj):
    # This is what it is now
    verts = list(low_obj.data.vertices)
    if verts:
        mw = low_obj.matrix_world
        bottom_z = min((mw @ v.co).z for v in verts)
        return bottom_z

if __name__ == "__main__":
    num_verts = 1000000 # Increased to 1M
    low_obj = MockObject(num_verts)

    # Warm up
    original_way(low_obj)
    optimized_way(low_obj)

    iterations = 20 # Fewer iterations for 1M verts

    t1 = timeit.timeit(lambda: original_way(low_obj), number=iterations)
    t2 = timeit.timeit(lambda: optimized_way(low_obj), number=iterations)

    print(f"Original way (1M verts): {t1:.4f}s")
    print(f"Optimized way (1M verts): {t2:.4f}s")
    print(f"Improvement: {(t1 - t2) / t1 * 100:.2f}%")
