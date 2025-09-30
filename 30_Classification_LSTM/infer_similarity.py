import os
import sys
import json
import argparse
import numpy as np
import pandas as pd
import torch
import torch.nn as nn


PLAYERS = ['Djo', 'Fed', 'Kei', 'Alc']
SEQUENCE_LENGTH = 48
N_FEATURES = 24


def normalize_sequence_center_scale(sequence: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    seq = sequence.copy()
    xs = seq[:, ::2]
    ys = seq[:, 1::2]
    cx = np.mean(xs)
    cy = np.mean(ys)
    xs -= cx
    ys -= cy
    seq[:, ::2] = xs
    seq[:, 1::2] = ys
    scale = np.std(seq)
    if scale < eps:
        scale = 1.0
    return seq / scale


class AugmentedLSTM(nn.Module):
    def __init__(self, input_size: int, hidden_size: int = 128, num_layers: int = 3, num_classes: int = 4, dropout: float = 0.5):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout if num_layers > 1 else 0)
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, num_classes),
        )

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        last_out = lstm_out[:, -1, :]
        return self.fc(last_out)


def load_sequence_from_csv(csv_path: str) -> np.ndarray:
    df = pd.read_csv(csv_path)
    # (1)を含むフレームを除外
    if 'frame_name' in df.columns:
        df = df[~df['frame_name'].str.contains(r"\(1\)", na=False)]
    keypoint_cols = [c for c in df.columns if c.startswith('kpt_')]
    seq = df[keypoint_cols].values
    if len(seq) < SEQUENCE_LENGTH:
        # 足りない分は最後のフレームを繰り返してパディング
        if len(seq) == 0:
            raise ValueError("Sequence empty")
        last = seq[-1:]
        pad_count = SEQUENCE_LENGTH - len(seq)
        seq = np.vstack([seq] + [last] * pad_count)
    if len(seq) > SEQUENCE_LENGTH:
        # 中央48フレームを使用
        start = (len(seq) - SEQUENCE_LENGTH) // 2
        seq = seq[start:start+SEQUENCE_LENGTH]
    return seq.astype(np.float32)


def infer(csv_path: str, model_path: str, device: str | None = None):
    device_torch = torch.device(device) if device else (torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu'))
    sequence = load_sequence_from_csv(csv_path)
    sequence = normalize_sequence_center_scale(sequence)

    model = AugmentedLSTM(input_size=N_FEATURES, hidden_size=128, num_layers=3, num_classes=len(PLAYERS), dropout=0.5).to(device_torch)
    state = torch.load(model_path, map_location=device_torch)
    model.load_state_dict(state)
    model.eval()

    x = torch.from_numpy(sequence).reshape(1, SEQUENCE_LENGTH, N_FEATURES).to(device_torch)
    with torch.no_grad():
        logits = model(x)
        probs = torch.softmax(logits, dim=1).cpu().numpy()[0]

    result = {
        'csv': csv_path,
        'model': model_path,
        'players': PLAYERS,
        'probabilities': {PLAYERS[i]: float(probs[i]) for i in range(len(PLAYERS))},
        'top1': {
            'player': PLAYERS[int(np.argmax(probs))],
            'score': float(np.max(probs))
        }
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True, help='Path to keypoints_with_tracks.csv')
    parser.add_argument('--model', default=os.path.join(os.path.dirname(__file__), 'best_augmented_model.pth'))
    parser.add_argument('--device', default=None)
    args = parser.parse_args()

    res = infer(args.csv, args.model, args.device)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == '__main__':
    sys.exit(main())


