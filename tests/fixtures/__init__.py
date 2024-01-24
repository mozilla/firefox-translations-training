import os
import shutil
import sys
from subprocess import CompletedProcess

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

ru_sample = """Маленькая девочка, увидев, что потеряла одну из своих красивых туфелек, рассердилась и сказала Ведьме: «Верни мне мою туфельку!»
«Я не буду, — парировала Ведьма, — потому что теперь это моя туфля, а не твоя».
«Ты злое существо!» - воскликнула Дороти. «Ты не имеешь права забирать у меня туфлю».
«Я все равно сохраню его, — сказала Ведьма, смеясь над ней, — и когда-нибудь я получу от тебя и другой».
Это так разозлило Дороти, что она взяла стоявшее рядом ведро с водой и облила им Ведьму, обмочив ее с головы до ног.
Мгновенно злая женщина громко вскрикнула от страха, а затем, когда Дороти с удивлением посмотрела на нее, Ведьма начала сжиматься и падать.
«Посмотри, что ты наделал!» она закричала. «Через минуту я растаю».
«Мне действительно очень жаль», — сказала Дороти, которая была по-настоящему напугана, увидев, что Ведьма тает, как коричневый сахар, у нее на глазах.
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
        """Create a folder or file name by joining it to the test directory."""
        return os.path.join(self.path, name)

    def load(self, name: str):
        """Load a text file"""
        with open(self.join(name), "r") as file:
            return file.read()

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

    def create_file(self, name: str, contents: str) -> str:
        """
        Creates a text file and returns the path to it.
        """
        text_path = os.path.join(self.path, name)
        if not os.path.exists(self.path):
            raise Exception(f"Directory for the text file does not exist: {self.path}")
        if os.path.exists(text_path):
            raise Exception(f"A file already exists and would be overwritten: {text_path}")

        print("Writing a text file to: ", text_path)
        with open(text_path, "w") as file:
            file.write(contents)

        return text_path


def fail_on_error(result: CompletedProcess[bytes]):
    """When a process fails, surface the stderr."""
    if not result.returncode == 0:
        for line in result.stderr.decode("utf-8").split("\n"):
            print(line, file=sys.stderr)

        raise Exception(f"{result.args[0]} exited with a status code: {result.returncode}")
