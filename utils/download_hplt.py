import argparse
import os
from multiprocessing import Pool
from typing import Optional

import pandas as pd
import requests

max_shards = 5
chunk_size = 30000
threads = 4


def process_row(row, lang, min_score):
    scores_length = len(row["scores"])
    langs_length = len(row["langs"])
    texts = row["text"].split("\n")
    texts_length = len(texts)

    if scores_length == langs_length and scores_length == texts_length:
        expanded_rows = []
        for score, lang_item, text_item in zip(row["scores"], row["langs"], texts):
            if lang_item == lang and score >= min_score:
                expanded_rows.append(text_item)
        return expanded_rows
    return []


def clean(df, lang, min_score):
    df = df.apply(lambda row: process_row(row, lang, min_score), axis=1).explode()
    df = df.dropna().drop_duplicates()
    return df


def download(params):
    lang, output, min_score = params
    print(f"Downloading {lang}...")
    resp = requests.get(f"https://data.hplt-project.org/one/monotext/cleaned/{lang}_map.txt")
    assert resp.status_code == 200
    shards = resp.content.decode().split()
    print(f"Number of shards for {lang}: {len(shards)}")

    for shard_id, shard in enumerate(shards):
        if shard_id == max_shards:
            break

        print(f"Reading shard {shard}")
        all_dfs = []
        with pd.read_json(shard, lines=True, compression="zstd", chunksize=chunk_size) as reader:
            for part_id, df in enumerate(reader):
                print(f"Filtering shard {shard}, part {part_id}")
                df_cleaned = clean(df, lang, min_score)
                all_dfs.append(df_cleaned)

        df = pd.concat(all_dfs)
        df = df.drop_duplicates()
        print(f"Final size for shard {shard}: {len(df)}")

        print(f"Saving shard {shard}")
        path = os.path.join(output, f"hplt_filtered_{lang}_{shard_id + 1}.txt.zst")
        df.to_csv(path, header=False, index=False, compression="zstd")
        with open(
            os.path.join(output, f"hplt_filtered_{lang}_{shard_id + 1}.count.txt"), "w"
        ) as f:
            f.write(str(len(df)))

        print(f"Saved to {path}")


def main(args_list: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,  # Preserves whitespace in the help text.
    )
    parser.add_argument("--langs", type=str, help="Comma separated list of languages")
    parser.add_argument("--output", type=str, help="Output directory")
    parser.add_argument("--min_score", type=float, help="Threshold")
    args = parser.parse_args(args_list)

    with Pool(processes=threads) as pool:
        pool.map(download, [(lang, args.output, args.min_score) for lang in args.langs.split(",")])


if __name__ == "__main__":
    main()
