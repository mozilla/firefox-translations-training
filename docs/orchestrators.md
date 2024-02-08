---
layout: default
title: Orchestrators
nav_order: 6
has_children: true
has_toc: false
---

# Orchestrators

An orchestrator is responsible for workflow management and parallelization.

Supported orchestrators:

- [Taskcluster](https://taskcluster.net/) - Mozilla task execution framework. It is also used for Firefox CI. 
  It provides access to the hybrid cloud workers (GCP + on-prem) with increased scalability and observability. 
  [Usage instructions](task-cluster.md).
- [Snakemake](https://snakemake.github.io/) - a file based orchestrator that can be used to run the pipeline locally or on a Slurm cluster. 
  [Usage instructions](snakemake.md). 

Mozilla has switched to Taskcluster for model training 
and the Snakemake pipeline is not maintained. 
Feel free to contirbute if you find bugs.
