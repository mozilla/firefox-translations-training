import os

from fixtures import DataDir, en_sample


def test_analyze_mono():
    data_dir = DataDir("test_analyze_mono")

    data_dir.mkdir("artifacts")
    data_dir.create_zst("news_2020.en.zst", en_sample)

    data_dir.run_task(
        "analyze-mono-news-crawl-en-news_2020",
    )

    data_dir.print_tree()

    assert os.path.isfile(data_dir.join("artifacts/distribution-words.png"))
    assert os.path.isfile(data_dir.join("artifacts/distribution-codepoints.png"))
