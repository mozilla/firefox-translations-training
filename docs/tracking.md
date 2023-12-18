# Metrics publication

A specific [module](/tracking) within this repository handles parsing training logs to extract Marian metrics in real time.

The parser supports reading logs from a Task Cluster environment, or a local directory containing multiple training data. It can publish metrics to an external dashboard, for example [Weight & Biases](https://wandb.ai/).
