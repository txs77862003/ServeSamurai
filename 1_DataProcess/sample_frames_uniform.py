import cv2, numpy as np, os, glob

CLIP_DIR = "clips"     # 切り出した動画の保存先
OUT_ROOT = "frames"    # 出力先（自動作成）
N = 90                 # 固定長にしたいフレーム数（例:90）

os.makedirs(OUT_ROOT, exist_ok=True)
clips = sorted(glob.glob(os.path.join(CLIP_DIR, "*.mp4")))

for clip in clips:
    stem = os.path.splitext(os.path.basename(clip))[0]
    out_dir = os.path.join(OUT_ROOT, stem)
    os.makedirs(out_dir, exist_ok=True)

    cap = cv2.VideoCapture(clip)
    T = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if T <= 0:
        continue

    # 等間隔で N 個のフレーム番号を選ぶ
    idx = np.linspace(0, T-1, N).astype(int)

    cur = 0
    for i in range(T):
        ret, frame = cap.read()
        if not ret:
            break
        if i in idx:
            cv2.imwrite(os.path.join(out_dir, f"{cur+1:04d}.jpg"), frame)
            cur += 1

    cap.release()
    print(f"[OK] {stem}: {cur}/{N} frames saved")