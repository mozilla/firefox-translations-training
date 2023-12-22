import os
import shutil

import zstandard as zstd

FIXTURES_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.abspath(os.path.join(FIXTURES_PATH, "../../data"))
TESTS_DATA = os.path.join(DATA_PATH, "tests_data")


en_sample = """The little girl, seeing she had lost one of her pretty shoes, grew angry, and said to the Witch, “Give me back my shoe!”
“I will not,” retorted the Witch, “for it is now my shoe, and not yours.”
“You are a wicked creature!” cried Dorothy. “You have no right to take my shoe from me.”
“I shall keep it, just the same,” said the Witch, laughing at her, “and someday I shall get the other one from you, too.”
This made Dorothy so very angry that she picked up the bucket of water that stood near and dashed it over the Witch, wetting her from head to foot.
Instantly the wicked woman gave a loud cry of fear, and then, as Dorothy looked at her in wonder, the Witch began to shrink and fall away.
“See what you have done!” she screamed. “In a minute I shall melt away.”
“I’m very sorry, indeed,” said Dorothy, who was truly frightened to see the Witch actually melting away like brown sugar before her very eyes.
"""

ca_sample = """La nena, en veure que havia perdut una de les seves boniques sabates, es va enfadar i va dir a la bruixa: "Torna'm la sabata!"
"No ho faré", va replicar la Bruixa, "perquè ara és la meva sabata, i no la teva".
"Ets una criatura dolenta!" va cridar la Dorothy. "No tens dret a treure'm la sabata".
"Me'l guardaré, igualment", va dir la Bruixa, rient-se d'ella, "i algun dia t'agafaré l'altre també".
Això va fer enfadar tant la Dorothy que va agafar la galleda d'aigua que hi havia a prop i la va llançar sobre la Bruixa, mullant-la de cap a peus.
A l'instant, la malvada dona va fer un fort crit de por, i aleshores, mentre la Dorothy la mirava meravellada, la Bruixa va començar a encongir-se i a caure.
"Mira què has fet!" ella va cridar. "D'aquí a un minut em fondreré".
"Ho sento molt, de veritat", va dir la Dorothy, que es va espantar veritablement de veure que la Bruixa es va desfer com el sucre moreno davant els seus mateixos ulls.
"""


class DataDir:
    """
    Creates a persistent data directory in data/tests_data/{dir_name} that will be
    cleaned out before a test run. This should help in persisting artifacts between test
    runs to manually verify the results.
    """

    def __init__(self, dir_name: str) -> None:
        self.path = os.path.join(TESTS_DATA, dir_name)

        # Ensure the base /data directory exists.
        os.makedirs(TESTS_DATA, exist_ok=True)

        # Clean up a previous run if this exists.
        if os.path.exists(self.path):
            shutil.rmtree(self.path)

        os.makedirs(self.path)
        print("Tests are using the subdirectory:", self.path)

    def join(self, name: str):
        return os.path.join(self.path, name)

    def create_zst(self, name: str, contents: str) -> str:
        """
        Creates a compressed zst file and returns the path to it.
        """
        zst_path = os.path.join(self.path, name)
        if not os.path.exists(self.path):
            raise Exception(f"Directory for the compressed file does not exist: {self.path}")
        if os.path.exists(zst_path):
            raise Exception(f"A file already exists and would be overwritten: {zst_path}")

        # Create the compressed file.
        cctx = zstd.ZstdCompressor()
        compressed_data = cctx.compress(contents.encode("utf-8"))

        print("Writing a compressed file to: ", zst_path)
        with open(zst_path, "wb") as file:
            file.write(compressed_data)

        return zst_path
