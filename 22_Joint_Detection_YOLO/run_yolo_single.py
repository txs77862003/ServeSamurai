#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], env: dict | None = None, cwd: str | None = None):
    print("$", " ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, cwd=cwd, text=True)
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
    code = proc.wait()
    if code != 0:
        raise SystemExit(code)


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def extract_frames_ffmpeg(video: Path, out_dir: Path, fps: int = 30, frames: int = 48):
    ensure_dir(out_dir)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video),
        "-vf", f"fps={fps}",
        "-frames:v", str(frames),
        str(out_dir / "%04d.jpg"),
    ]
    run(cmd)


def main():
    parser = argparse.ArgumentParser(description="Run YOLO keypoint extraction for a single clip")
    parser.add_argument("--clip-name", required=True, help="Clip name directory under frames/Cleaned_Data/players/<player>/")
    parser.add_argument("--player", default="User", help="Player folder name (default: User)")
    parser.add_argument("--video", help="Optional: input mp4 to first extract 48 frames at 30fps")
    parser.add_argument("--run-active-track", action="store_true", help="Run find_most_active_tracks.py after YOLO")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    frames_root = project_root / "frames"
    target_frames_dir = frames_root / "Cleaned_Data" / "players" / args.player / args.clip_name

    if args.video:
        video = Path(args.video).resolve()
        print(f"[info] Extracting frames from video: {video}")
        extract_frames_ffmpeg(video, target_frames_dir, fps=30, frames=48)

    if not target_frames_dir.exists() or not any(target_frames_dir.glob("*.jpg")):
        print(f"[error] No frames found in {target_frames_dir}")
        return 2

    # Prepare source dir for copy BEFORE backup
    source_dir_for_copy = target_frames_dir

    # Backup existing frames and scope to target only
    frames_backup = project_root / "frames_all"
    if not frames_backup.exists() and frames_root.exists():
        print(f"[info] Backup frames -> {frames_backup}")
        frames_root.rename(frames_backup)
    # If we just backed up, target_frames_dir moved under frames_all. Adjust source accordingly.
    if not source_dir_for_copy.exists():
        maybe = frames_backup / "Cleaned_Data" / "players" / args.player / args.clip_name
        if maybe.exists():
            source_dir_for_copy = maybe
    ensure_dir(frames_root)

    # Recreate the minimal structure and copy target dir under new frames
    minimal_parent = frames_root / "Cleaned_Data" / "players" / args.player
    ensure_dir(minimal_parent)
    temp_target = minimal_parent / args.clip_name
    if not temp_target.exists():
        print(f"[info] Copy target frames -> {temp_target}")
        shutil.copytree(source_dir_for_copy, temp_target)

    # Run YOLO.py with envs
    env = os.environ.copy()
    env.setdefault("ULTRALYTICS_CACHE_DIR", "/tmp")
    env.setdefault("TMPDIR", "/tmp")
    env.setdefault("HOME", "/tmp")
    env.setdefault("YOLO_MODEL_PATH", str(project_root / "yolo11n-pose.pt"))
    print("[info] Run YOLO.py for target clip only")
    run([sys.executable, str(project_root / "22_Joint_Detection_YOLO/YOLO.py")], env=env, cwd=str(project_root / "22_Joint_Detection_YOLO"))

    # Move produced coords/vis back into main frames directory
    produced_coords = frames_root / "pose_coords_yolo"
    produced_vis = frames_root / "pose_visualization"
    dest_coords = project_root / "frames" / "pose_coords_yolo"
    dest_vis = project_root / "frames" / "pose_visualization"
    if produced_coords.exists():
        ensure_dir(dest_coords.parent)
        try:
            # If source and destination are the same path, skip moving
            if produced_coords.resolve() == dest_coords.resolve():
                print("[info] pose_coords_yolo already in destination. Skip moving.")
            else:
                if dest_coords.exists():
                    shutil.rmtree(dest_coords)
                produced_coords.rename(dest_coords)
        except FileNotFoundError:
            # In case the directory was removed between checks; ignore
            pass
    if produced_vis.exists():
        ensure_dir(dest_vis.parent)
        try:
            if produced_vis.resolve() == dest_vis.resolve():
                print("[info] pose_visualization already in destination. Skip moving.")
            else:
                if dest_vis.exists():
                    shutil.rmtree(dest_vis)
                produced_vis.rename(dest_vis)
        except FileNotFoundError:
            pass

    # Restore frames
    print("[info] Restore original frames directory")
    shutil.rmtree(frames_root, ignore_errors=True)
    if frames_backup.exists():
        frames_backup.rename(frames_root)

    if args.run_active_track:
        print("[info] Run find_most_active_tracks.py (quiet)")
        try:
            devnull = open(os.devnull, 'w')
            subprocess.Popen(
                [sys.executable, str(project_root / "22_Joint_Detection_YOLO/find_most_active_tracks.py")],
                cwd=str(project_root / "22_Joint_Detection_YOLO"),
                stdout=devnull,
                stderr=devnull,
            ).wait()
        finally:
            try:
                devnull.close()
            except Exception:
                pass

    # APIは新標準パス pose_tracks/players/... を参照する方針に統一

    print("[done] YOLO single clip processing completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


