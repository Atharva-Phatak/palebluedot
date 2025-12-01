class Metric:
    def __init__(self):
        self.reset()

    def reset(self):
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.sum += val * n
        self.count += n

    @property
    def avg(self):
        if self.count == 0:
            return 0
        return self.sum / self.count


class MetricRunner:
    def __init__(self):
        self.metrics = {}

    def update(self, name, val, n=1):
        if name not in self.metrics:
            self.metrics[name] = Metric()
        self.metrics[name].update(val, n)

    def get_avg(self, name):
        return self.metrics[name].avg

    def reset(self, name):
        self.metrics[name].reset()

    @property
    def tracked_metrics(self):
        return {name: metric.avg for name, metric in self.metrics.items()}
