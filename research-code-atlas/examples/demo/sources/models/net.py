from .blocks import Block


class Net:
    def __init__(self, dim):
        self.block = Block(dim)
        self.dim = dim

    def forward(self, x):
        h = self.block.run(x)
        return self.head(h)

    def head(self, h):
        def scale(v):
            return v * 2

        return [scale(v) for v in h]

    def __call__(self, x):
        return self.forward(x)
