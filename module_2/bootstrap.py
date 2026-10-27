"""Download pinned public experiment inputs only into ignored module_2/local.

Run explicitly: python -m module_2.bootstrap
Dataset terms and annotation documentation: https://www.blinkingmatters.com/research
No raw dataset or video belongs in Git.
"""
import hashlib
from pathlib import Path
import urllib.request
import zipfile

SG1="f9463063f37816759179f9204ac2edf072af83cb"
SG4="059705b87bed8067a006d3c4095aebb274b06c98"
ROOT=Path(__file__).resolve().parent/"local"
ASSETS=[
    ("https://www.blinkingmatters.com/files/upload/research/eyeblink8.zip","eyeblink8.zip","856cb82f3437f3c0d94633027cb74cf74186920ca5926aeebb630d715eba9295"),
    ("https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task","face_landmarker.task","64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"),
]


def main():
    ROOT.mkdir(exist_ok=True)
    for url,name,digest in ASSETS:
        path=ROOT/name
        if not path.exists():
            print("Downloading",url,flush=True)
            temporary=path.with_suffix(path.suffix+".part")
            urllib.request.urlretrieve(url,temporary)
            if hashlib.sha256(temporary.read_bytes()).hexdigest()!=digest:raise ValueError("asset checksum mismatch")
            temporary.replace(path)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError("asset checksum mismatch: "+name)
    with zipfile.ZipFile(ROOT/"eyeblink8.zip") as archive:
        target=(ROOT/"eyeblink8").resolve()
        for member in archive.namelist():
            if not (target/member).resolve().is_relative_to(target):raise ValueError("unsafe archive path")
        archive.extractall(target)
    for ref,remote,local in [(SG1,"module_1/scripts/sg1_detector.py","sg1/sg1_detector.py"),
                             (SG1,"module_1/scripts/sg1_contract.py","sg1/sg1_contract.py"),
                             (SG4,"module_4/D2-SG4.ipynb","sg4.ipynb")]:
        path=ROOT/local;path.parent.mkdir(parents=True,exist_ok=True)
        url=f"https://raw.githubusercontent.com/Sananismm/CV_Drowsinees_Detection/{ref}/{remote}"
        urllib.request.urlretrieve(url,path)
        print(local,hashlib.sha256(path.read_bytes()).hexdigest())
    print("Ready:",ROOT)


if __name__=="__main__":main()
