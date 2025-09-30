"""
テニスサーブ分析用データユーティリティ
 - 動画の取り込み（コピー）
 - 動画からフレーム抽出（デフォルト30fps）
"""

import os
import shutil
from typing import List, Dict, Optional
import argparse
import subprocess
import cv2
from pathlib import Path

class TennisServeVideoManager:
    """テニスサーブ動画の管理クラス"""
    
    def __init__(self, source_dir: str = "../tennis_videos", target_dir: str = "tennis_videos"):
        """
        初期化
        
        Args:
            source_dir: 動画ファイルのソースディレクトリ
            target_dir: 処理済み動画の保存ディレクトリ
        """
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        
        # ディレクトリを作成
        self.target_dir.mkdir(exist_ok=True)
        
        print(f"ソースディレクトリ: {self.source_dir}")
        print(f"ターゲットディレクトリ: {self.target_dir}")

    def extract_frames(self, frames_root: str = "frames", fps: int = 30, player_override: Optional[str] = None) -> List[Path]:
        """
        対象の動画（target_dir配下）からフレームを抽出し、frames配下に保存

        Args:
            frames_root: フレーム保存先のルートディレクトリ
            fps: 抽出フレームレート（30fps推奨）

        Returns:
            抽出したクリップのディレクトリ一覧
        """
        frames_root_path = Path(frames_root)
        frames_root_path.mkdir(exist_ok=True)

        def infer_player_from_filename(file_stem: str) -> str:
            """ファイル名から選手名を推定して返す（Kei/Fed/Djo）。未知は Other。

            例: kei_*, nishi*, fed_*, roger*, djo*, djoko*
            """
            s = file_stem.lower()
            # Kei Nishikori
            if s.startswith("kei") or s.startswith("nishi"):
                return "Kei"
            # Roger Federer
            if s.startswith("fed") or s.startswith("roger"):
                return "Fed"
            # Novak Djokovic
            if s.startswith("djo") or s.startswith("djoko") or "djoko" in s:
                return "Djo"
            # Carlos Alcaraz
            if s.startswith("alc") or "alcaraz" in s or "carlitos" in s:
                return "Alc"
            return "Other"

        def infer_player_from_path(p: Path) -> Optional[str]:
            """親ディレクトリ名などから選手名を推定。"""
            parts = [str(part).lower() for part in p.parts]
            for token in parts:
                if token in ("kei", "nishi", "nishikori"):
                    return "Kei"
                if token in ("fed", "federer", "roger"):
                    return "Fed"
                if token in ("djo", "djoko", "djokovic", "novak"):
                    return "Djo"
                if token in ("alc", "alcaraz", "carlitos"):
                    return "Alc"
            return None

        extracted_dirs: List[Path] = []
        video_files = self.list_processed_videos()

        def mirror_existing_images() -> None:
            # すでに抽出済みのフレーム画像が tennis_videos 配下にある場合はそれをミラー
            image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
            any_mirrored = False
            for dirpath, dirnames, filenames in os.walk(self.target_dir):
                image_files = [f for f in filenames if Path(f).suffix.lower() in image_exts]
                if not image_files:
                    continue
                any_mirrored = True
                rel = Path(dirpath).relative_to(self.target_dir)
                # 既存データに含まれる冗長な Cleaned_Data/<player>/ を除去
                if len(rel.parts) >= 2 and rel.parts[0].lower() == "cleaned_data":
                    rel = Path(*rel.parts[2:]) if len(rel.parts) > 2 else Path("")
                # 優先度: 明示指定 > パスから推定 > 名前から推定 > Other
                player = player_override or infer_player_from_path(Path(dirpath)) or infer_player_from_filename(str(rel.parts[0] if rel.parts else rel.name)) or "Other"
                # frames/Cleaned_data/players/<Player>/<rel>/ に配置
                clip_dir = frames_root_path / "Cleaned_data" / "players" / player / rel
                clip_dir.mkdir(parents=True, exist_ok=True)
                for name in sorted(image_files):
                    src = Path(dirpath) / name
                    dst = clip_dir / name
                    if not dst.exists():
                        shutil.copy2(src, dst)
                if clip_dir not in extracted_dirs:
                    extracted_dirs.append(clip_dir)
                print(f"✓ 画像ミラー: {clip_dir}")
            if not any_mirrored:
                print("フレーム抽出対象が見つかりませんでした（動画も画像も無し）。")

        if not video_files:
            print("動画ファイルが見つかりません。画像フレームのミラーを試みます…")
            mirror_existing_images()
            return extracted_dirs

        for video_path in video_files:
            clip_stem = video_path.stem
            # 優先度: 明示指定 > 親パスから推定 > ファイル名から推定
            player = player_override or infer_player_from_path(video_path) or infer_player_from_filename(clip_stem)
            # frames/Cleaned_data/players/<Player>/<ClipName>
            clip_dir = frames_root_path / "Cleaned_data" / "players" / player / clip_stem
            clip_dir.mkdir(parents=True, exist_ok=True)

            print(f"[FRAMES] {video_path.name} -> {clip_dir} @ {fps}fps")

            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                print(f"✗ 動画を開けませんでした: {video_path}")
                continue

            # 総フレーム数と実FPS（参考）
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            in_fps = cap.get(cv2.CAP_PROP_FPS) or fps
            interval = max(1, int(round(in_fps / fps)))

            frame_index = 0
            saved = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_index % interval == 0:
                    out_name = f"frame_{saved:04d}.jpg"
                    out_path = clip_dir / out_name
                    cv2.imwrite(str(out_path), frame)
                    saved += 1
                frame_index += 1

            cap.release()
            print(f"✓ 抽出完了: {saved} 枚 (元の総フレーム: {total_frames}, 入力FPS: {in_fps:.2f})")
            extracted_dirs.append(clip_dir)

        # 付随して tennis_videos 配下の既存フレーム画像もミラー
        mirror_existing_images()

        return extracted_dirs
    
    def scan_videos(self) -> List[Path]:
        """
        ソースディレクトリから動画ファイルをスキャン
        
        Returns:
            動画ファイルのパスリスト
        """
        if not self.source_dir.exists():
            print(f"ソースディレクトリ '{self.source_dir}' が存在しません。")
            return []
        
        video_files = []
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv']
        
        for file_path in self.source_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                video_files.append(file_path)
        
        print(f"ソースディレクトリで{len(video_files)}個の動画ファイルが見つかりました。")
        return video_files
    
    def copy_video(self, source_path: Path, target_name: Optional[str] = None) -> bool:
        """
        動画ファイルをコピー
        
        Args:
            source_path: ソースファイルのパス
            target_name: 保存するファイル名（指定しない場合は元のファイル名を使用）
            
        Returns:
            コピー成功の可否
        """
        try:
            if not target_name:
                target_name = source_path.name
            
            target_path = self.target_dir / target_name
            
            # ファイルをコピー
            shutil.copy2(source_path, target_path)
            print(f"動画をコピーしました: {target_path}")
            return True
            
        except Exception as e:
            print(f"コピーエラー: {e}")
            return False
    
    def list_processed_videos(self) -> List[Path]:
        """
        処理済みの動画ファイル一覧を取得
        
        Returns:
            動画ファイルのパスリスト
        """
        video_files: List[Path] = []
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv']
        
        # 再帰的に探索（孫ディレクトリの動画も対象）
        for file_path in self.target_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                video_files.append(file_path)
        
        return video_files
    

def main():
    """CLIエントリポイント"""
    parser = argparse.ArgumentParser(description="テニスサーブ動画ユーティリティ")
    parser.add_argument("action", choices=["scan-copy", "extract-frames", "all"], nargs="?", default="extract-frames",
                        help="実行するアクション (既定: extract-frames)")
    parser.add_argument("--source", dest="source_dir", default="../tennis_videos",
                        help="コピー元ディレクトリ")
    parser.add_argument("--target", dest="target_dir", default="tennis_videos",
                        help="コピー先(および抽出対象)ディレクトリ")
    parser.add_argument("--frames-root", dest="frames_root", default="frames",
                        help="フレーム出力先ルート")
    parser.add_argument("--fps", dest="fps", type=int, default=30, help="フレーム抽出FPS")
    parser.add_argument("--player", dest="player", type=str, default=None, help="選手名を強制指定 (Kei/Fed/Djo)")

    args = parser.parse_args()

    print("テニスサーブ動画ユーティリティ")
    print("=" * 40)

    manager = TennisServeVideoManager(source_dir=args.source_dir, target_dir=args.target_dir)

    if args.action in ("scan-copy", "all"):
        print(f"\n1) ソースから動画をコピー中...")
        video_files = manager.scan_videos()
        success_count = 0
        for i, video_path in enumerate(video_files, 1):
            print(f"[{i}/{len(video_files)}] {video_path.name} をコピー中...")
            success = manager.copy_video(video_path)
            success_count += int(bool(success))
        print(f"コピー結果: {success_count}/{len(video_files)} 成功")

    if args.action in ("extract-frames", "all"):
        print(f"\n2) フレーム抽出中 ({args.fps}fps)...")
        out_dirs = manager.extract_frames(frames_root=args.frames_root, fps=args.fps, player_override=args.player)
        if not out_dirs:
            print("抽出対象がありません。'tennis_videos' に動画を配置してください。")
        else:
            for d in out_dirs:
                print(f"- {d}")

if __name__ == "__main__":
    main()
