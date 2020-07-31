class DataPatch:
    def __init__(self, label=None, points=None, image=None):
        self.label = label
        self.points = points
        self.image = image


class DataCollection:
    def __init__(self, points=None):
        self.points = points


class DataPipeline:
    def __init__(self, labels=None):
        self.labels = labels

