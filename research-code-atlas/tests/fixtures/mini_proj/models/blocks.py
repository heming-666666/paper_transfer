from utils.helpers import normalize


class Block:
    def __init__(self, dim):
        self.dim = dim

    def run(self, x):
        # 安全测试：</script><script>window.__x=1</script>
        return normalize(x)
