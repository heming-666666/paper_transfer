import argparse
from models.net import Net as Model
from utils import helpers
from utils.helpers import seed_all
import losses


def build(cfg):
    return Model(cfg["dim"])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--unused_flag", default=0)
    args = p.parse_args()
    seed_all(0)
    model = build({"dim": 4})
    print("lr", args.lr)
    for epoch in range(args.epochs):
        if epoch % 2 == 0:
            loss, parts = losses.total_loss(model, [1.0, 2.0])
        else:
            loss = helpers.normalize([3.0, 4.0])
    fn = getattr(helpers, "dyn_" + "x")
    fn()
    return helpers.fact(3)


if __name__ == "__main__":
    main()
