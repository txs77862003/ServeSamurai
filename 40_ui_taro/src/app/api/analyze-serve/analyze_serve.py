#!/usr/bin/env python3
import sys
import json
import math


def main():
    try:
        raw = sys.stdin.read()
        sys.stderr.write(f"[py] received bytes: {len(raw.encode('utf-8'))}\n")
        payload = json.loads(raw or '{}')

        video_path = payload.get('videoPath')
        segments = payload.get('segments') or []
        if not video_path:
            raise ValueError('videoPath is required')
        if not segments:
            raise ValueError('segments is required')

        seg0 = segments[0]
        start = float(seg0.get('start', 0))
        end = float(seg0.get('end', 0))
        duration = max(0.0, end - start)
        fps = 30
        total_frames = int(math.floor(duration * fps))

        # 簡易な疑似分析（将来的にYOLO/LSTMへ差し替え）
        analysis = {
            'serveType': 'Detected Serve',
            'accuracy': 86,
            'power': 79,
            'timing': 91,
            'technique': {
                'stance': 'Good',
                'grip': 'Continental',
                'toss': 'Stable',
                'follow_through': 'Excellent',
            },
            'recommendations': [
                'トスの高さとタイミングを一定に保つ',
                '膝の沈み込みをやや大きくして下半身の推進力を活用',
                'フォロースルーを長く取りフィニッシュで静止'
            ],
            'videoMetrics': {
                'duration': duration,
                'fps': fps,
                'totalFrames': total_frames,
            },
        }

        clips = [{
            'id': 1,
            'startTime': start,
            'endTime': end,
            'duration': duration,
            'analysis': {
                'serveQuality': 'Good',
                'ballSpeed': 132,
                'spinRate': 2450,
                'trajectory': 'Consistent arc'
            }
        }]

        out = {
            'success': True,
            'analysis': analysis,
            'clips': clips,
        }
        sys.stderr.write("[py] analysis prepared, writing JSON...\n")
        sys.stdout.write(json.dumps(out))
        sys.stdout.flush()
        return 0
    except Exception as e:
        sys.stderr.write(f"[py][error] {type(e).__name__}: {e}\n")
        err = {'success': False, 'error': str(e)}
        sys.stdout.write(json.dumps(err))
        sys.stdout.flush()
        return 1


if __name__ == '__main__':
    sys.exit(main())


