---
layout: default
title: Taskcluster
nav_order: 1
parent: Orchestrators
---

# Taskcluster

[Taskcluster](https://taskcluster.net/) is a Mozilla task execution framework. It powers Firefox CI and
provides access to the hybrid cloud workers (GCP or on-prem) 
which increases scalability and observability compared to [Snakemake](snakemake.md). 

We use [Taskcluster taskgraph](https://taskcluster-taskgraph.readthedocs.io/en/latest/) to define the DAG 
(Directly Acyclic Graph) of the pipeline steps.

## Running training

1. Create a new branch in the git repo and push. 
   It is useful to experiment with code and also not to get the caches invalidated if you need to restart training and some new changes were landed in the main branch.
    
2. Go to Github CI for the commit you want to run training for and find a Decision Task

![Find CI](img/github-tc-ci.png)

3. Go to CI and press "View task in Taskcluster". 
   Make sure you are authenticated in the TC interface. It is required to run tasks. 
   However, already running tasks can be viewed without authentication.

![Go to TC](img/github-view-task.png)

4. In TC interface navigate to a parent Task Group

![Go to TaskGroup](img/tc-task-group.png)

5. Press "Train" in the 3-dot menu for actions

![Choose action](img/tc-train-action.png)

6. Copy a config prepared in advance and press "train". See the example TC config [here](https://github.com/mozilla/firefox-translations-training/tree/main/configs/tc.prod.yml). 
   You can find directions on how to configure training in the [Model training guide](training-guide.md).

![Start training](img/tc-train.png)

## Checking the status of training

1. Look at the scheduled tasks. They should be visible under the Train action.

![Action tasks](img/tc-train-action-tasks.png)

2. Press any task. Here you can look at the logs and artifacts produced by the task.
   
![A task](img/tc-task.png)

3. Navigate to a parent Task Group again (it is a different one than for the Train Action). 
   Here you can see all the scheduled tasks in a more convenient interface with filtering.

![All tasks](img/tc-all-tasks.png)

## Resource monitoring

CPU, GPU, RAM, and other metrics are available in GCP. The [Firefox Translations Worker Monitoring Dashboard](https://console.cloud.google.com/monitoring/dashboards/builder/a6c8749a-75e2-490a-a7ea-628960c70ea8;startTime=2024-01-25T14:43:04Z;endTime=2024-01-25T20:43:04Z?project=fxci-production-level1-workers) is a good starting point for observing resource utilization during training. You should filter this dashboard on the `name` of the instance running your training task. You can find this name at the top of the training log as the first part of the `public-hostname`. Eg:
```
[taskcluster 2024-01-24T18:43:50.869Z]     "public-hostname": "translations-1-b-linux-v100-gpu-4-300g-uwfi5olorq6omun0mr1wgq.c.fxci-production-level1-workers.internal",
```

Once you have the name you can use the "Add filter" button near the top of the page to limit the data shown. You should end up with a dashboard similar to this when done:
![Firefox Translations Worker Monitoring Dashboard filtered to show CPU, RAM, and GPU usage of a single instance](img/gcp-monitoring.png).

If you want to customize your own dashboard with different widgets you can create a new Dashboard by clicking the "Firefox Translations Worker Monitoring" followed by "Create Dashboard". (A detailed tutorial on how to create these dashboards is out of scope for this document, but there are many resources available online, and the UI is fairly intuitive.)

## Rerunning

Quite often you need to rerun the pipeline after making fixes or when a task fails.

It is possible to manually cancel a task with the Cancel task action.

![Cancel](img/tc-cancel.png)

After the fixes were implemented, push again and restart the pipeline with the same procedure 
as described in the "Running training" section.

### Caching

Some steps might be already cached from the previous run depending on the fixes. 
For example if only a config setting that affects the last task was changed,
or if nothing changed at all the pipeline might restart from the failed/cancelled step.

Warning: even a slight refactoring of the upstream steps can invalidate caches for the whole pipeline completely, 
so it's better to be careful with that when experimenting with the later stages of the pipeleine.


## Running up to a specific step

Change `target-stage: all` in the training config to a stage that corresponds to another TC step. 
For example, to download, clean and merge the training corpus use:
```
target-stage: merge-corpus
```
that corresponds to `stage: merge-corpus` in [/taskcluster/ci/merge-corpus/kind.yml](https://github.com/mozilla/firefox-translations-training/taskcluster/ci/merge-corpus/kind.yml):
```
tasks:
    merge-corpus:
        label: merge-corpus-{src_locale}-{trg_locale}
        description: merge corpus for {src_locale}-{trg_locale}
        attributes:
            dataset-category: train
            stage: merge-corpus
```

## Interactive Tasks

Taskcluster allows authorized users to run so-called [interactive tasks](https://docs.taskcluster.net/docs/reference/workers/docker-worker/features#feature-interactive). These tasks allow users to gain a shell in the same environment that a pipeline step runs in. This can often be useful for quicker debugging or testing of ideas.

To start an interactive task, follow these steps:

1. Go to the task you want an interactive version of, eg: https://firefox-ci-tc.services.mozilla.com/tasks/DZvVQ-VUTPSyPBBS13Bwfg

2. Click the "Edit" button in the three dots menu

3. Click "Edit" on the modal that pops up

4. Click the "Interactive" toggle in the top left

5. Reduce the maxRunTime to a best guess at how long you'll need the task and worker running for. (We pay for every minute a worker runs - so they should not be kept running, eg: overnight.)

6. Adjust the payload to run `sleep 7200` instead of running the bash script. It's based to keep all of the environment set up and run_task part of the command, abut then replace the actual script running to the sleep command.

```
     command:
    - bash
    - '-c'
    - 'sleep 7200'
```

For generic-worker tasks (those needing a GPU), use:
```
     command:
    - - bash
      - '-c'
      - 'sleep 7200'
```

(docker-worker tasks have an `image` section in the payload)

7. Click "Create Task"

After a few minutes you should be able to get a shell (a link will show up in the tab when it's ready).

8. Grab the fetches

Assuming you kept the `run_task` in the command, then you can fetch the content.

```sh
chmod +x fetch-content
./fetch-content task-artifacts
```
