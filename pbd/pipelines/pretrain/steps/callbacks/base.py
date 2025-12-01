class Callback:
    def on_train_start(self, trainer):
        pass

    def on_step_start(self, trainer):
        pass

    def on_step_end(self, trainer):
        pass

    def on_exception(self, trainer, exception):
        pass

    def on_train_end(self, trainer):
        pass
