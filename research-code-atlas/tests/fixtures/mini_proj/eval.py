from models.net import Net
import losses


def evaluate():
    net = Net(8)
    out = net.forward([1.0, 2.0, 3.0])
    total, parts = losses.total_loss(net, out)
    return {"total": total, "n": len(out)}


if __name__ == "__main__":
    evaluate()
