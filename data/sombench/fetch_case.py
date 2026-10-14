"""Fetch one viewer metadata row and its matching immutable SomBench assets."""
import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASET = 'nasa-ibm-ai4science/Sombench-WAC-Crater-Detection'


def download(url, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination
    partial = destination.with_suffix(destination.suffix + '.part')
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Quantum-Lunar-Case/1.0'})
            with urllib.request.urlopen(request, timeout=120) as response, partial.open('wb') as handle:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    handle.write(block)
            partial.replace(destination)
            return destination
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fetch_case(row_index=0, revision=None):
    import pyarrow.parquet as pq
    import ijson
    if row_index < 0:
        raise ValueError('row index must be nonnegative')
    if revision is None:
        with urllib.request.urlopen('https://huggingface.co/api/datasets/' + DATASET, timeout=60) as response:
            revision = json.load(response)['sha']
    base = 'https://huggingface.co/datasets/' + DATASET + '/resolve/' + urllib.parse.quote(revision, safe='') + '/'
    cache = ROOT / 'data/sombench/cache' / revision
    metadata = download(base + 'metadata.parquet', cache / 'metadata.parquet')
    rows = pq.read_table(metadata).to_pylist()
    if row_index >= len(rows):
        raise ValueError(f'Row {row_index} is outside the {len(rows)} metadata rows')
    row = rows[row_index]
    split = str(row['DATASET']).lower()
    if split not in ('train', 'val', 'test'):
        raise ValueError(f'Unsupported annotation split: {split}')
    stem = Path(row['WAC_VIS_TILE']).stem
    print(f'Row {row_index}: {stem}, source split {split}', flush=True)
    image_relative = 'images_tiff/' + stem + '.tif'
    image = download(base + image_relative, cache / (stem + '.tif'))
    annotations_path = download(base + split + '.json', cache / (split + '.json'))
    with annotations_path.open('rb') as handle:
        info = next((item for item in ijson.items(handle, 'images.item', use_float=True)
                     if Path(item['file_name']).stem == stem), None)
    if info is None:
        raise ValueError('Metadata tile has no matching COCO image in its assigned split')
    with annotations_path.open('rb') as handle:
        annotations = [ann for ann in ijson.items(handle, 'annotations.item', use_float=True)
                       if ann['image_id'] == info['id']]
    if not annotations:
        raise ValueError('Matched tile has no crater annotations')
    manifest = {
        'dataset': DATASET, 'dataset_revision': revision, 'metadata_row_index': row_index,
        'viewer_config': 'metadata', 'viewer_split': 'train', 'annotation_split': split,
        'metadata': row, 'image_info': info, 'annotations': annotations,
        'local_image': image.relative_to(ROOT).as_posix(),
        'source_urls': {'image': base + image_relative, 'annotations': base + split + '.json',
                        'metadata': base + 'metadata.parquet'},
        'sha256': {'image': sha256(image), 'annotations': sha256(annotations_path), 'metadata': sha256(metadata)},
        'label_kind': 'catalog-derived circular polygons; approximate rim reference',
        'license': 'CC-BY-4.0', 'attribution': 'NASA-IBM AI4Science SomBench; Robbins (2019) crater catalog',
    }
    output = ROOT / 'data/sombench/real_case' / f'row{row_index}_case.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Saved {output} ({len(annotations)} crater annotations)', flush=True)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--row', type=int, default=0)
    parser.add_argument('--revision')
    args = parser.parse_args()
    fetch_case(args.row, args.revision)
