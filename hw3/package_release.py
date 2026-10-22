"""Package the trained model and complete predictions as GitHub release assets."""
import hashlib
import json
import zipfile

from prepare_data import ROOT, write_json
from public_links import MODEL_DOWNLOAD, REPOSITORY


def archive(destination, files):
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as out:
        for path, relative in files:
            out.write(path, relative)
    return {'filename': destination.name, 'bytes': destination.stat().st_size,
            'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
            'url': REPOSITORY + '/releases/download/hw3-news-bert-v1/' + destination.name}


def main():
    release = ROOT / '.release'
    release.mkdir(exist_ok=True)
    model = ROOT / 'models/news-bert'
    model_files = [(p, 'models/news-bert/' + p.name) for p in model.iterdir() if p.is_file()]
    license_file = ROOT / 'models/bert-base-chinese/README.md'
    model_files.append((license_file, 'PRETRAINED_MODEL_CARD.md'))
    weight_asset = archive(release / 'hw3-news-bert.zip', model_files)
    prediction_files = [(p, str(p.relative_to(ROOT)).replace('\\', '/'))
                        for p in (ROOT / 'data/predictions/news-bert').glob('*.jsonl')]
    prediction_files += [(p, 'sources/' + corpus + '/' + p.name)
                         for corpus in ['lunyu', 'cclue']
                         for p in (ROOT / 'data' / corpus / 'upstream').glob('*')
                         if p.name in ['LICENSE', 'README.md']]
    prediction_asset = archive(release / 'hw3-predictions.zip', prediction_files)
    write_json(ROOT / 'results/release_assets.json', {'assets': [weight_asset, prediction_asset],
        'model_restore': 'Extract hw3-news-bert.zip inside hw3/; it creates models/news-bert/.',
        'prediction_restore': 'Extract hw3-predictions.zip inside hw3/; it creates data/predictions/news-bert/.',
        'model_weight_sha256': hashlib.sha256((model / 'model.safetensors').read_bytes()).hexdigest()})
    print(json.dumps([weight_asset, prediction_asset], indent=2))


if __name__ == '__main__':
    main()
