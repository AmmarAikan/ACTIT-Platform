"""Clean-v2 entrypoint using the frozen Clean-v1 training implementation."""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.training import bert_dnrti_clean_v1 as training


training.INTERNAL_IDS = {
    "first_subword": "clean_v2_first_subword",
    "bio_aware": "clean_v2_bio_aware",
}


if __name__ == "__main__":
    training.main()
