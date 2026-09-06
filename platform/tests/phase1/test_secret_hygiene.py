from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def test_no_secrets_tracked():
 assert not list(ROOT.glob('runtime/**/.env'))
