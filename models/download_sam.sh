#!/usr/bin/env sh
# Download a Segment Anything checkpoint into this folder.
#   ./download_sam.sh            -> SAM 2.1 base (~320 MB; the default, recommended)
#   ./download_sam.sh sam2.1_t   -> SAM 2.1 tiny  (~80 MB, fastest, for CPU-only servers)
#   ./download_sam.sh sam2.1_s   -> SAM 2.1 small (~185 MB)
#   ./download_sam.sh sam2.1_l   -> SAM 2.1 large (~900 MB, most accurate)
#   ./download_sam.sh vit_b      -> original SAM (~375 MB; also vit_l, vit_h)
# The server uses /models/sam2.1_b.pt by default (SAM_CHECKPOINT); when that
# file is missing it uses the best checkpoint it finds in this folder.
set -e
cd "$(dirname "$0")"
model="${1:-sam2.1_b}"
case "$model" in
  sam2.1_t|sam2.1_s|sam2.1_b|sam2.1_l)
    file="$model.pt"
    url="https://github.com/ultralytics/assets/releases/download/v8.3.0/$file" ;;
  vit_b) file=sam_vit_b_01ec64.pth; url="https://dl.fbaipublicfiles.com/segment_anything/$file" ;;
  vit_l) file=sam_vit_l_0b3195.pth; url="https://dl.fbaipublicfiles.com/segment_anything/$file" ;;
  vit_h) file=sam_vit_h_4b8939.pth; url="https://dl.fbaipublicfiles.com/segment_anything/$file" ;;
  *) echo "unknown model: $model (sam2.1_t, sam2.1_s, sam2.1_b, sam2.1_l, vit_b, vit_l or vit_h)"; exit 1 ;;
esac
echo "Downloading $url"
if command -v curl >/dev/null 2>&1; then curl -fL -o "$file" "$url"; else wget -O "$file" "$url"; fi
echo "Saved models/$file"
