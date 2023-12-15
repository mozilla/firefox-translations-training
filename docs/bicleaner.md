---
layout: default
title: Bicleaner
parent: Data cleaning
---
# Bicleaner

Bicleaner is a tool that aims at detecting noisy sentence pairs in a parallel corpus. The classifier scores parallel sentences from 0 to 1 where 0 means a very noisy translation and 1 is a good translation. In the pipeline, Bicleaner AI will be used first if [the language is available][ai-releases], otherwise it will fallback to the original non-AI Bicleaner.

See:
  * [https://github.com/bitextor/bicleaner-ai](https://github.com/bitextor/bicleaner-ai)
  * [https://github.com/bitextor/bicleaner](https://github.com/bitextor/bicleaner)

For supported languages see:
  * [Bicleaner AI Releases][ai-releases]
  * [Bicleaner Releases][releases]

New language releases should be added to: `taskcluster/ci/fetch/bicleaner.yml`

## How to configure for training

The configuration specifies a default threshold and a per-dataset threshold. A sentence pair will be kept if its score is **above** the given threshold.

- `0.5` should be a [good default value].
- Increase the threshold for noisier datasets.
- Set the threshold to `0` to skip cleaning entirely.

## Recommendations for specific datasets

| Data set      | Threshold | Reason                   |
| ------------- | --------- | -------                  |
| OpenSubtitles | 0.8       | This is a noiser dataset |
| ParaCrawl     | 0         | This dataset has already been cleaned by bicleaner. See [Bicleaner AI: Bicleaner Goes Neural], section 4.2.2 |

## Example config:

```
  bicleaner:
    default-threshold: 0.5
    dataset-thresholds:
      opus_CCAligned/v1: 0.7
      opus_OpenSubtitles/v2018: 0.8
      opus_ParaCrawl/v9: 0
      ...
```

[good default value]: https://github.com/bitextor/bicleaner-ai/wiki/How-to-train-your-Bicleaner-AI#bicleaning-a-corpus
[ai-releases]: https://github.com/bitextor/bicleaner-ai-data/releases
[releases]: https://github.com/bitextor/bicleaner-data/releases
[Bicleaner AI: Bicleaner Goes Neural]: https://aclanthology.org/2022.lrec-1.87.pdf
