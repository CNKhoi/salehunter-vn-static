"""Upload a strict allowlist of SaleHunter Static files. Requires HF_TOKEN secret."""
import os, tempfile, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=('README.md','index.html','main.js','styles.css','config.js','data/offers.json','data/excluded_codes.json')
def stage(target):
    for rel in FILES:
        src=(ROOT/'hf/README.md') if rel=='README.md' else ROOT/rel
        if not src.is_file():raise FileNotFoundError(src)
        dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
def main():
    token=os.getenv('HF_TOKEN')
    if not token:raise SystemExit('HF_TOKEN missing: set a write-scoped token in GitHub Actions secrets')
    from huggingface_hub import HfApi
    with tempfile.TemporaryDirectory() as d:
        stage(Path(d))
        HfApi(token=token).upload_folder(repo_id='khoiminh333/salehunter-vn-v2',repo_type='space',folder_path=d,commit_message='chore: SaleHunter V3.2 static sync')
if __name__=='__main__':main()
