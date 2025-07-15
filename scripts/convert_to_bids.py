import os
import subprocess
import json
import glob
from pathlib import Path
import pydicom

# Configuration
SOURCE_ROOT = Path('/mnt/d/Biomag/MS_AV_REST_MRT/MS_AV_REST_MRT/data/raw')
TARGET_ROOT = Path('/mnt/e/MS_AV_REST_MRT/BIDS')

# Sequence-to-BIDS mappings
MODALITY_MAP = {
    'rs_01': 'func',
    'rs_02': 'func',
    'stim_01': 'func',
    'mprage_01': 'anat',
    'mprage_02': 'anat',
    'flair_01': 'anat'
}
SUFFIX_MAP = {
    'rs_01': 'task-rest_run-1_bold',
    'rs_02': 'task-rest_run-2_bold',
    'stim_01': 'task-stim_run-1_bold',
    'mprage_01': 'T1w',
    'mprage_02': 'T1w2',
    'flair_01': 'FLAIR'
}

# Ensure target subdirectories exist
TARGET_ROOT.mkdir(parents=True, exist_ok=True)

# Iterate over subjects
for subj_dir in SOURCE_ROOT.glob('REST_MRT_*__0'):
    if not subj_dir.is_dir():
        continue
    subj_name = subj_dir.name
    num = subj_name.replace('REST_MRT_', '').replace('__0', '')
    try:
        dec_num = int(num)
    except ValueError:
        print(f"Skipping invalid subject folder: {subj_name}")
        continue
    subj_id = f"sub-{dec_num:03d}"

    for seq, modality in MODALITY_MAP.items():
        src_seq = subj_dir / seq
        if not src_seq.exists():
            print(f"{subj_id}: Sequence folder missing: {seq}")
            continue

        bids_dir = TARGET_ROOT / subj_id / modality
        bids_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{subj_id}_{SUFFIX_MAP[seq]}"
        out_nii = bids_dir / f"{filename}.nii.gz"
        out_json = bids_dir / f"{filename}.json"

        # Skip if already exists
        if out_nii.exists() and out_json.exists():
            print(f"{subj_id} {seq}: already converted, skipping.")
            continue

        # Call dcm2niix for conversion
        cmd = [
            'dcm2niix', '-z', 'y', '-f', filename,
            '-o', str(bids_dir), str(src_seq)
        ]
        print(f"Converting {subj_id} {seq} ...")
        subprocess.run(cmd, check=True)

        # Supplement JSON sidecar with BIDS fields
        if out_json.exists():
            header_json = json.loads(out_json.read_text())
            # Load first DICOM file for header info
            dcm_files = list(src_seq.glob('*.dcm'))
            if not dcm_files:
                dcm_files = list(src_seq.glob('MR*'))
            if dcm_files:
                ds = pydicom.dcmread(str(dcm_files[0]), stop_before_pixels=True)
                # Map DICOM tags to BIDS JSON
                header_json.setdefault('RepetitionTime', ds.get('RepetitionTime'))
                header_json.setdefault('EchoTime', ds.get('EchoTime'))
                header_json.setdefault('FlipAngle', ds.get('FlipAngle'))
                peg = ds.get('InPlanePhaseEncodingDirection', None) or ds.get('PhaseEncodingDirection', None)
                if peg:
                    header_json.setdefault('PhaseEncodingDirection', peg)
                px = ds.get('PixelSpacing', None)
                if px:
                    header_json.setdefault('PixelSpacing', list(px))
                st = ds.get('SliceThickness', None)
                if st:
                    header_json.setdefault('SliceThickness', st)
                # Write back JSON
                out_json.write_text(json.dumps(header_json, indent=4))
                print(f"Supplemented JSON for {filename}")
            else:
                print(f"No DICOM files found for header parsing in {src_seq}")
        else:
            print(f"JSON sidecar not found for {filename}, skipping supplement.")

# Create dataset_description.json if missing
ds_desc = TARGET_ROOT / 'dataset_description.json'
if not ds_desc.exists():
    desc = {
        'Name': 'MS_AV_REST_MRT Study',
        'BIDSVersion': '1.8.0',
        'DatasetType': 'raw',
        'Authors': []
    }
    ds_desc.write_text(json.dumps(desc, indent=4))
    print('Created dataset_description.json')

# Create participants.tsv if missing
participants_tsv = TARGET_ROOT / 'participants.tsv'
if not participants_tsv.exists():
    header = ['participant_id']
    rows = [subj.name.replace('REST_MRT_', '').replace('__0', '') for subj in SOURCE_ROOT.glob('REST_MRT_*__0')]
    with participants_tsv.open('w') as f:
        f.write('# participants.tsv')
        f.write('\t'.join(header) + '\n')
        for r in rows:
            pid = f"sub-{int(r):03d}"
            f.write(f"{pid}\n")
    print('Created participants.tsv')

print('BIDS conversion complete.')
