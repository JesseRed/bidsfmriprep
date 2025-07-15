#!/usr/bin/env bash
set -euo pipefail

# 1) Pfade anpassen (WSL-Mountpoints)
SOURCE_ROOT="/mnt/d/Biomag/MS_AV_REST_MRT/data/raw"
TARGET_ROOT="/mnt/e/MS_AV_REST_MRT/BIDS"
LOGFILE="${TARGET_ROOT}/missing_sequences_log.txt"

# 2) Sequenz → BIDS Mapping
declare -A MODALITY_MAP=(
  ["rs_01"]="func"
  ["rs_02"]="func"
  ["stim_01"]="func"
  ["mprage_01"]="anat"
  ["mprage_02"]="anat"
  ["flair_01"]="anat"
)
declare -A SUFFIX_MAP=(
  ["rs_01"]="task-rest_run-1_bold"
  ["rs_02"]="task-rest_run-2_bold"
  ["stim_01"]="task-stim_run-1_bold"
  ["mprage_01"]="T1w"
  ["mprage_02"]="T1w2"
  ["flair_01"]="FLAIR"
)

# 3) Log-Datei initialisieren
echo "=== Debug-Log BIDS-Konvertierung ($(date)) ===" > "$LOGFILE"

# 4) Alle Subjekte durchlaufen
for subj_path in "${SOURCE_ROOT}"/REST_MRT_*__0; do
  [ -d "$subj_path" ] || continue
  subj_name=$(basename "$subj_path")
  # Nummer extrahieren: REST_MRT_05__0 → 05
  num=${subj_name#REST_MRT_}
  num=${num%%__0}
  
  dec_num=$((10#$num))
  printf -v subj_id "sub-%03d" "$dec_num"
  echo "subj_id: $subj_id"
  echo "--- $subj_id ($subj_name)" >> "$LOGFILE"

  # Jede Sequenz abarbeiten
  for seq in "${!MODALITY_MAP[@]}"; do
    src_seq="${subj_path}/${seq}"
    echo "Check: $src_seq" >> "$LOGFILE"
    if [ ! -d "$src_seq" ]; then
      echo "   → Ordner fehlt: $seq" >> "$LOGFILE"
      echo "[$subj_id] fehlt Ordner $seq" >> "$LOGFILE"
      continue
    fi

    modality=${MODALITY_MAP[$seq]}
    suffix=${SUFFIX_MAP[$seq]}
    bids_dir="${TARGET_ROOT}/${subj_id}/${modality}"
    mkdir -p "$bids_dir"

    filename="${subj_id}_${suffix}"
    out_file="${bids_dir}/${filename}.nii.gz"

    # ← EXISTENZ-CHECK
    if [ -f "$out_file" ]; then
       echo "   → $out_file existiert bereits – überspringe $seq" >> "$LOGFILE"
       continue
    fi

    # 5) dcm2niix aufrufen, weil Output fehlt
    #    -z y: gzip
    #    -f: Dateiname template
    #    -o: Ausgabeverzeichnis
    echo "   → konvertiere $seq → ${out_file}" >> "$LOGFILE"
    dcm2niix -z y -f "$filename" -o "$bids_dir" "$src_seq" \
      || echo "   !!! Fehler bei dcm2niix für $seq" >> "$LOGFILE"
  done
done

echo "🎉 Fertig: BIDS-4D-Volumes & Debug-Log unter $LOGFILE" | tee -a "$LOGFILE"
