from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
IDS=('outline','prefect','docling-serve','mineru','ragflow','langfuse','kag-poc','libreoffice','clamav')
def test_runtime_standard_files():
 for cid in IDS:
  p=ROOT/'runtime'/cid
  assert all((p/n).is_file() for n in ('README.md','.env.example','smoke-test.sh','backup-notes.md'))
