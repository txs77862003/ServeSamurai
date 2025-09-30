import pandas as pd
import numpy as np
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
plt.rcParams['font.family'] = 'DejaVu Sans'

class TennisPoseDataset(Dataset):
    """テニスポーズデータセット用のPyTorch Dataset"""
    def __init__(self, sequences, labels=None):
        self.sequences = torch.FloatTensor(sequences)
        self.labels = torch.LongTensor(labels) if labels is not None else None
        
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        if self.labels is not None:
            return self.sequences[idx], self.labels[idx]
        return self.sequences[idx]

class DataAugmentation:
    """テニスポーズデータの拡張クラス"""
    
    @staticmethod
    def normalize_sequence_center_scale(sequence: np.ndarray, eps: float = 1e-6) -> np.ndarray:
        """各クリップで重心平行移動し、全座標をスケール正規化。
        - 重心: 全キーポイントの平均 (フレーム単位ではなくクリップ全体)
        - スケール: 全フレーム全座標の標準偏差
        """
        seq = sequence.copy()
        # 全フレームのxとyをそれぞれ抽出
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

    @staticmethod
    def rotate_sequence(sequence, angle_degrees):
        """シーケンスを回転"""
        angle_rad = np.radians(angle_degrees)
        cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
        
        # 重心を計算
        center_x = np.mean(sequence[:, ::2])  # x座標
        center_y = np.mean(sequence[:, 1::2])  # y座標
        
        augmented = sequence.copy()
        
        for i in range(0, sequence.shape[1], 2):  # x, y座標ペア
            x_coords = sequence[:, i] - center_x
            y_coords = sequence[:, i+1] - center_y
            
            # 回転変換
            new_x = x_coords * cos_a - y_coords * sin_a + center_x
            new_y = x_coords * sin_a + y_coords * cos_a + center_y
            
            augmented[:, i] = new_x
            augmented[:, i+1] = new_y
        
        return augmented
    
    @staticmethod
    def scale_sequence(sequence, scale_factor):
        """シーケンスをスケーリング"""
        # 重心を計算
        center_x = np.mean(sequence[:, ::2])
        center_y = np.mean(sequence[:, 1::2])
        
        augmented = sequence.copy()
        
        for i in range(0, sequence.shape[1], 2):
            x_coords = (sequence[:, i] - center_x) * scale_factor + center_x
            y_coords = (sequence[:, i+1] - center_y) * scale_factor + center_y
            
            augmented[:, i] = x_coords
            augmented[:, i+1] = y_coords
        
        return augmented
    
    @staticmethod
    def add_noise(sequence, noise_std=0.01):
        """ガウシアンノイズを追加"""
        noise = np.random.normal(0, noise_std, sequence.shape)
        return sequence + noise
    
    @staticmethod
    def time_warp(sequence, warp_factor=0.1):
        """時間軸の歪みを追加"""
        n_frames = sequence.shape[0]
        warp_points = np.random.uniform(-warp_factor, warp_factor, n_frames)
        warp_points = np.cumsum(warp_points)
        
        # 線形補間で新しいフレームを生成
        original_indices = np.arange(n_frames)
        new_indices = original_indices + warp_points
        new_indices = np.clip(new_indices, 0, n_frames-1)
        
        augmented = np.zeros_like(sequence)
        for i in range(sequence.shape[1]):
            augmented[:, i] = np.interp(new_indices, original_indices, sequence[:, i])
        
        return augmented
    
    @staticmethod
    def augment_sequence(sequence, num_augmentations=1):
        """複数の拡張手法を組み合わせてデータを生成"""
        augmented_sequences = [sequence]
        
        for _ in range(num_augmentations):
            # ランダムに拡張手法を選択（位相ロバスト性を高める新拡張を追加）
            augmentation_type = np.random.choice([
                'rotate', 'scale', 'noise', 'time_warp',
                'time_scale', 'frame_drop', 'post_impact_mask', 'localized_noise', 'impact_realign'
            ])

            if augmentation_type == 'rotate':
                angle = np.random.uniform(-5, 5)  # 位相崩し過ぎを避けて小さめ
                aug_seq = DataAugmentation.rotate_sequence(sequence, angle)
            elif augmentation_type == 'scale':
                scale = np.random.uniform(0.95, 1.05)
                aug_seq = DataAugmentation.scale_sequence(sequence, scale)
            elif augmentation_type == 'noise':
                noise_std = np.random.uniform(0.003, 0.01)
                aug_seq = DataAugmentation.add_noise(sequence, noise_std)
            elif augmentation_type == 'time_warp':
                warp = np.random.uniform(0.05, 0.10)
                aug_seq = DataAugmentation.time_warp(sequence, warp)
            elif augmentation_type == 'time_scale':
                scale_factor = np.random.uniform(0.92, 1.08)
                aug_seq = DataAugmentation.time_scale_sequence(sequence, scale_factor)
            elif augmentation_type == 'frame_drop':
                aug_seq = DataAugmentation.drop_random_frames_with_interp(sequence, max_drops=2)
            elif augmentation_type == 'post_impact_mask':
                aug_seq = DataAugmentation.post_impact_mask_or_noise(sequence, window=3, mode='noise')
            elif augmentation_type == 'localized_noise':
                aug_seq = DataAugmentation.add_localized_noise(sequence, base_std=0.006)
            elif augmentation_type == 'impact_realign':
                aug_seq = DataAugmentation.realign_sequence_to_impact(sequence, target_index=sequence.shape[0]//2)

            # 生成後は重心平行移動＋スケール正規化を維持
            aug_seq = DataAugmentation.normalize_sequence_center_scale(aug_seq)
            augmented_sequences.append(aug_seq)
        
        return augmented_sequences

    # --------------- 位相ロバスト性向上のための新規拡張 ---------------
    @staticmethod
    def estimate_impact_index(sequence: np.ndarray, safeguard_center_bias: bool = True) -> int:
        """インパクト近傍のフレームを推定。
        近似として、フレーム間速度（全キーポイントの合計速度）が最大の箇所をインパクトとみなす。
        safeguard_center_bias=True の場合、中心付近に軽い事前バイアスを与える。
        """
        if sequence.shape[0] <= 2:
            return max(0, sequence.shape[0] // 2)
        diffs = np.diff(sequence, axis=0)
        # 各フレームの速度量（フレームt→t+1）: L2ノルムの総和
        speeds = np.sqrt((diffs ** 2).reshape(diffs.shape[0], -1).sum(axis=1))
        # 長さをフレーム数に合わせる（最後の速度を複製して同じ長さに）
        speeds_full = np.concatenate([speeds, speeds[-1:]], axis=0)
        if safeguard_center_bias:
            n = sequence.shape[0]
            center = (n - 1) / 2.0
            # 中心からの距離に応じて軽いガウス重みを加算
            idxs = np.arange(n)
            bias = np.exp(-((idxs - center) ** 2) / (2 * (0.2 * n) ** 2))
            speeds_full = speeds_full + 0.05 * bias
        impact_idx = int(np.argmax(speeds_full))
        return impact_idx

    @staticmethod
    def realign_sequence_to_impact(sequence: np.ndarray, target_index: int) -> np.ndarray:
        """推定インパクトフレームが target_index に来るように時間シフト（端は複製で埋める）。"""
        n = sequence.shape[0]
        impact = DataAugmentation.estimate_impact_index(sequence)
        shift = target_index - impact
        if shift == 0:
            return sequence.copy()
        # シフト適用（端はエッジ複製）
        result = np.zeros_like(sequence)
        for t in range(n):
            src = np.clip(t - shift, 0, n - 1)
            result[t] = sequence[src]
        return result

    @staticmethod
    def time_scale_sequence(sequence: np.ndarray, scale_factor: float) -> np.ndarray:
        """時間スケーリング（速度変化）。補間で長さを元に戻す。最後にインパクト再アライン。"""
        n, d = sequence.shape
        if n <= 1 or abs(scale_factor - 1.0) < 1e-6:
            return sequence.copy()
        # 新しい時間軸
        orig_idx = np.arange(n)
        new_len = max(2, int(round(n * scale_factor)))
        new_idx = np.linspace(0, n - 1, new_len)
        scaled = np.zeros((new_len, d), dtype=sequence.dtype)
        for i in range(d):
            scaled[:, i] = np.interp(new_idx, orig_idx, sequence[:, i])
        # 元の長さに再サンプル
        back_idx = np.linspace(0, new_len - 1, n)
        restored = np.zeros_like(sequence)
        for i in range(d):
            restored[:, i] = np.interp(back_idx, np.arange(new_len), scaled[:, i])
        # インパクトを中央付近に再アライン
        restored = DataAugmentation.realign_sequence_to_impact(restored, target_index=n // 2)
        return restored

    @staticmethod
    def drop_random_frames_with_interp(sequence: np.ndarray, max_drops: int = 2) -> np.ndarray:
        """少数フレームをドロップし補間で復元。インパクト後側に軽いバイアス。"""
        n, d = sequence.shape
        if n <= 3 or max_drops <= 0:
            return sequence.copy()
        impact = DataAugmentation.estimate_impact_index(sequence)
        num_drop = np.random.randint(1, max_drops + 1)
        # インパクト後にやや偏った確率でドロップ候補を選ぶ
        probs = np.ones(n)
        if impact < n - 1:
            probs[impact+1:] *= 1.5
        probs = probs / probs.sum()
        drop_idxs = np.sort(np.random.choice(np.arange(1, n - 1), size=num_drop, replace=False, p=probs[1:n-1] / probs[1:n-1].sum()))
        keep_mask = np.ones(n, dtype=bool)
        keep_mask[drop_idxs] = False
        kept = sequence[keep_mask]
        # 元の長さに補間で戻す
        kept_n = kept.shape[0]
        new_idx = np.linspace(0, kept_n - 1, n)
        restored = np.zeros_like(sequence)
        for i in range(d):
            restored[:, i] = np.interp(new_idx, np.arange(kept_n), kept[:, i])
        # 軽く平滑化
        if n >= 5:
            restored[1:-1] = (restored[:-2] + 2 * restored[1:-1] + restored[2:]) / 4.0
        return restored

    @staticmethod
    def post_impact_mask_or_noise(sequence: np.ndarray, window: int = 3, mode: str = 'noise', noise_std: float = 0.006) -> np.ndarray:
        """インパクト直後の短区間の情報量を抑える（ノイズ付与または弱マスク）。"""
        n, d = sequence.shape
        result = sequence.copy()
        impact = DataAugmentation.estimate_impact_index(sequence)
        start = min(n - 1, max(impact + 1, 0))
        end = min(n, start + max(1, window))
        if start >= end:
            return result
        if mode == 'noise':
            noise = np.random.normal(0, noise_std, size=(end - start, d))
            result[start:end] += noise
        else:
            # 平均へ収束させる弱マスク
            seg = result[start:end]
            mean_vec = seg.mean(axis=0, keepdims=True)
            alpha = 0.5
            result[start:end] = alpha * seg + (1 - alpha) * mean_vec
        return result

    @staticmethod
    def add_localized_noise(sequence: np.ndarray, base_std: float = 0.006) -> np.ndarray:
        """末端（中心から遠い）キーポイントほど強めのノイズを与える局所ノイズ。"""
        n, d = sequence.shape
        result = sequence.copy()
        # 各キーポイントの半径（全フレーム平均）を見て重み付け
        xs = sequence[:, ::2]
        ys = sequence[:, 1::2]
        # クリップ内中心へ正規化済み前提だが、念のため中心再計算
        cx = xs.mean()
        cy = ys.mean()
        radii = np.sqrt(((xs - cx) ** 2 + (ys - cy) ** 2)).mean(axis=0)  # 形状: (num_kpts)
        # 正規化して[0.8, 1.2]程度の重みへ
        if radii.size > 0:
            r_min, r_max = radii.min(), radii.max()
            if r_max - r_min < 1e-9:
                weights = np.ones_like(radii)
            else:
                weights = 0.8 + 0.4 * (radii - r_min) / (r_max - r_min)
        else:
            weights = np.array([])
        # 各キーポイントごとにノイズ強度を変える
        for k in range(len(weights)):
            std_k = base_std * weights[k]
            result[:, 2*k] += np.random.normal(0, std_k, size=n)
            result[:, 2*k+1] += np.random.normal(0, std_k, size=n)
        return result

class AugmentedLSTM(nn.Module):
    """データ拡張対応LSTMモデル"""
    def __init__(self, input_size, hidden_size=64, num_layers=2, num_classes=3, dropout=0.3):
        super(AugmentedLSTM, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM層
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, 
                           batch_first=True, dropout=dropout if num_layers > 1 else 0)
        
        # 全結合層
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, num_classes)
        )
        
    def forward(self, x):
        # LSTMの出力
        lstm_out, (hidden, cell) = self.lstm(x)
        
        # 最後のタイムステップの出力を使用
        last_output = lstm_out[:, -1, :]
        
        # 全結合層
        output = self.fc(last_output)
        
        return output

class AugmentedTennisPoseTrainer:
    """データ拡張対応テニスポーズLSTMモデルの訓練クラス"""
    def __init__(self, data_path, target_samples_per_player=18, device=None):
        self.data_path = data_path
        self.device = device if device else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.scaler = StandardScaler()
        # Cleaned_data/players 配下の構成に合わせてプレイヤーを拡張
        self.players = ['Djo', 'Fed', 'Kei', 'Alc']
        self.sequence_length = 48
        self.n_features = 24
        self.target_samples = target_samples_per_player
        
        print(f"使用デバイス: {self.device}")
        print(f"目標サンプル数/選手: {self.target_samples}")
        
    def load_and_augment_data(self):
        """データを読み込んで拡張"""
        print("=== データ読み込みと拡張 ===")
        
        all_data = []
        all_labels = []
        player_stats = {}
        per_player_sequences = {}
        per_player_meta = {}
        
        for i, player in enumerate(self.players):
            print(f"\n選手 {player} のデータを処理中...")
            player_path = os.path.join(self.data_path, player)
            sequences = []
            seq_meta = []
            
            # 元データを読み込み
            for seq_dir in os.listdir(player_path):
                seq_path = os.path.join(player_path, seq_dir)
                if os.path.isdir(seq_path):
                    csv_file = os.path.join(seq_path, 'keypoints_with_tracks.csv')
                    if os.path.exists(csv_file):
                        df = pd.read_csv(csv_file)
                        df_clean = df[~df["frame_name"].str.contains(r"\(1\)", na=False)]
                        keypoint_cols = [col for col in df_clean.columns if col.startswith('kpt_')]
                        sequence = df_clean[keypoint_cols].values
                        
                        if len(sequence) == self.sequence_length:
                            sequences.append(sequence)
                            seq_meta.append({"player": player, "clip": seq_dir, "origin": "orig"})
            
            print(f"  元データ: {len(sequences)} シーケンス")
            
            # シーケンスを正規化（重心平行移動＋スケール正規化）
            sequences = [DataAugmentation.normalize_sequence_center_scale(seq) for seq in sequences]
            per_player_sequences[player] = sequences
            per_player_meta[player] = seq_meta
        
        # クラス間バランス拡張
        max_count = max(len(per_player_sequences[p]) for p in self.players)
        target_per_class = max(self.target_samples, max_count)
        print(f"  クラス間ターゲット: {target_per_class} シーケンス/選手")
        
        for i, player in enumerate(self.players):
            sequences = per_player_sequences[player]
            meta_list = per_player_meta[player]

            # 位相バケット: 前/インパクト±/後
            def bucket_of(seq: np.ndarray) -> str:
                n = seq.shape[0]
                imp = DataAugmentation.estimate_impact_index(seq)
                center = n // 2
                if imp <= center - 2:
                    return 'pre'
                elif imp >= center + 2:
                    return 'post'
                return 'impact'

            buckets = {'pre': [], 'impact': [], 'post': []}
            buckets_meta = {'pre': [], 'impact': [], 'post': []}
            for s, m in zip(sequences, meta_list):
                b = bucket_of(s)
                buckets[b].append(s)
                buckets_meta[b].append(m)

            # 目標比率 前:インパクト±:後 = 1:1:2（端数は post → impact → pre の順で配分）
            ratio = {'pre': 1, 'impact': 1, 'post': 2}
            ratio_sum = sum(ratio.values())
            desired = {k: int(np.floor(target_per_class * ratio[k] / ratio_sum)) for k in ratio}
            remainder = target_per_class - sum(desired.values())
            for k in ['post', 'impact', 'pre']:
                if remainder <= 0:
                    break
                desired[k] += 1
                remainder -= 1

            # まず既存を集約
            augmented_sequences = []
            augmented_meta = []
            for k in ['pre', 'impact', 'post']:
                augmented_sequences.extend(buckets[k])
                augmented_meta.extend(buckets_meta[k])

            # 不足分を位相優先で拡張
            def pick_from_bucket(name: str, counters: dict[str, int]):
                arr = buckets[name]
                if len(arr) == 0:
                    # フォールバック: データが多い順で探す
                    for alt in ['post', 'impact', 'pre']:
                        if len(buckets[alt]) > 0:
                            name = alt
                            arr = buckets[alt]
                            break
                if len(arr) == 0:
                    return None, None
                idx0 = counters.get(name, 0) % len(arr)
                counters[name] = idx0 + 1
                return arr[idx0], buckets_meta[name][idx0]

            counters: dict[str, int] = {}
            while True:
                counts = {'pre': 0, 'impact': 0, 'post': 0}
                for s in augmented_sequences:
                    counts[bucket_of(s)] += 1
                short = {k: max(0, desired[k] - counts[k]) for k in counts}
                if sum(short.values()) == 0:
                    break
                target_bucket = max(short.items(), key=lambda kv: kv[1])[0]
                base_seq, base_m = pick_from_bucket(target_bucket, counters)
                if base_seq is None:
                    break
                aug_seq = DataAugmentation.augment_sequence(base_seq, 1)[1]
                aug_seq = DataAugmentation.normalize_sequence_center_scale(aug_seq)
                augmented_sequences.append(aug_seq)
                augmented_meta.append({"player": player, "clip": base_m.get("clip", "unknown"), "origin": "aug"})

            # 過剰ならランダムサブサンプル
            if len(augmented_sequences) > target_per_class:
                idxs = np.random.choice(len(augmented_sequences), target_per_class, replace=False)
                sequences = [augmented_sequences[k] for k in idxs]
                meta_list = [augmented_meta[k] for k in idxs]
                print(f"  {player}: サンプリング後 {len(sequences)} シーケンス")
            else:
                sequences = augmented_sequences
                meta_list = augmented_meta
                print(f"  {player}: 拡張後 {len(sequences)} シーケンス (目標 {target_per_class})")
            
            labels = np.full(len(sequences), i)
            all_data.extend(sequences)
            all_labels.extend(labels)
            if 'all_meta' not in locals():
                all_meta = []
            all_meta.extend(meta_list)
            player_stats[player] = { 'final': len(sequences) }
        
        X = np.array(all_data)
        y = np.array(all_labels)
        
        # クリップ正規化済みなので、ここでの標準化は不実施（必要ならコメント解除）
        # n_sequences, n_frames, n_features = X.shape
        # X_flat = X.reshape(-1, n_features)
        # X_normalized = self.scaler.fit_transform(X_flat)
        # X = X_normalized.reshape(n_sequences, n_frames, n_features)
        
        print(f"\n全データ: {X.shape}")
        for i, player in enumerate(self.players):
            count = np.sum(y == i)
            print(f"  {player}: {count} シーケンス")
        return X, y, player_stats, all_meta
    
    def train_model(self, X, y, meta=None):
        """拡張データでLSTMモデルを訓練"""
        print("\n=== 拡張データLSTMモデル訓練 ===")
        if meta is None:
            meta = [{} for _ in range(len(X))]
        X_train, X_test, y_train, y_test, meta_train, meta_test = train_test_split(
            X, y, meta, test_size=0.3, random_state=42, stratify=y
        )
        
        train_dataset = TennisPoseDataset(X_train, y_train)
        test_dataset = TennisPoseDataset(X_test, y_test)
        train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)
        
        # LSTMハイパーパラメータ調整
        model = AugmentedLSTM(
            input_size=self.n_features,
            hidden_size=128,
            num_layers=3,
            num_classes=len(self.players),
            dropout=0.5
        ).to(self.device)
        
        print(f"モデルパラメータ数: {sum(p.numel() for p in model.parameters())}")
        
        class_counts = np.bincount(y_train)
        class_weights = 1.0 / np.maximum(class_counts, 1)
        class_weights = class_weights / class_weights.sum() * len(class_weights)
        class_weights_tensor = torch.FloatTensor(class_weights).to(self.device)
        
        criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
        optimizer = optim.Adam(model.parameters(), lr=0.001)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=8, factor=0.5)
        
        best_val_loss = float('inf')
        patience = 15
        patience_counter = 0
        best_model_path = 'best_augmented_model.pth'
        
        # 学習履歴
        train_losses: list[float] = []
        train_accuracies: list[float] = []
        val_losses: list[float] = []
        val_accuracies: list[float] = []
        
        print("訓練開始...")
        for epoch in range(200):
            model.train()
            train_loss = 0
            train_correct = 0
            train_total = 0
            for batch_x, batch_y in train_loader:
                batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                optimizer.zero_grad()
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                train_total += batch_y.size(0)
                train_correct += (predicted == batch_y).sum().item()
            
            model.eval()
            val_loss = 0
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for batch_x, batch_y in test_loader:
                    batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                    outputs = model(batch_x)
                    loss = criterion(outputs, batch_y)
                    val_loss += loss.item()
                    _, predicted = torch.max(outputs.data, 1)
                    val_total += batch_y.size(0)
                    val_correct += (predicted == batch_y).sum().item()
            
            train_loss /= max(len(train_loader), 1)
            train_acc = 100 * train_correct / max(train_total, 1)
            val_loss /= max(len(test_loader), 1)
            val_acc = 100 * val_correct / max(val_total, 1)
            
            scheduler.step(val_loss)
            
            # 早期停止: Val Loss基準
            improved = val_loss < best_val_loss - 1e-6
            if improved:
                best_val_loss = val_loss
                patience_counter = 0
                torch.save(model.state_dict(), best_model_path)
            else:
                patience_counter += 1

            # ログ用に履歴を保存
            train_losses.append(train_loss)
            train_accuracies.append(train_acc)
            val_losses.append(val_loss)
            val_accuracies.append(val_acc)
            
            if epoch % 10 == 0:
                print(f'Epoch [{epoch+1}/120], Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%, Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%')
            if patience_counter >= patience:
                print(f'Early stopping at epoch {epoch+1} (best Val Loss: {best_val_loss:.4f})')
                break
        
        model.load_state_dict(torch.load(best_model_path))
        
        # 最終評価
        model.eval()
        all_predictions = []
        all_targets = []
        per_sample = []
        with torch.no_grad():
            test_seen = 0
            for batch_x, batch_y in test_loader:
                batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                outputs = model(batch_x)
                loss_vec = nn.functional.cross_entropy(outputs, batch_y, reduction='none')
                _, predicted = torch.max(outputs.data, 1)
                for i_in_batch in range(batch_y.size(0)):
                    all_predictions.append(int(predicted[i_in_batch].cpu().item()))
                    all_targets.append(int(batch_y[i_in_batch].cpu().item()))
                    per_sample.append({
                        "loss": float(loss_vec[i_in_batch].cpu().item()),
                        "target": int(batch_y[i_in_batch].cpu().item()),
                        "pred": int(predicted[i_in_batch].cpu().item()),
                        "meta": meta_test[test_seen]
                    })
                    test_seen += 1
        
        print(f"\n最良Val Loss: {best_val_loss:.4f}")
        print("\n分類レポート:")
        print(classification_report(all_targets, all_predictions, target_names=self.players))
        
        # 混同行列
        cm = confusion_matrix(all_targets, all_predictions)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                   xticklabels=self.players, yticklabels=self.players)
        plt.title('Confusion Matrix (Augmented LSTM)')
        plt.ylabel('True Player')
        plt.xlabel('Predicted Player')
        plt.tight_layout()
        plt.savefig('confusion_matrix_augmented.png')
        plt.show()
        
        # 高ロス検体の上位5件を表示
        worst = sorted(per_sample, key=lambda d: d["loss"], reverse=True)[:5]
        print("\n=== 高ロス検体 (Top-5) ===")
        for w in worst:
            m = w.get("meta", {})
            print(f"loss={w['loss']:.4f} target={self.players[w['target']]} pred={self.players[w['pred']]} clip={m.get('clip','?')} origin={m.get('origin','?')}")

        # 訓練履歴の可視化
        self.plot_training_history(train_losses, train_accuracies, val_losses, val_accuracies)
        
        return model
    
    def plot_training_history(self, train_losses, train_accs, val_losses, val_accs):
        """訓練履歴を可視化"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
        
        # 精度
        ax1.plot(train_accs, label='Training Accuracy')
        ax1.plot(val_accs, label='Validation Accuracy')
        ax1.set_title('Model Accuracy (Augmented LSTM)')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Accuracy (%)')
        ax1.legend()
        ax1.grid(True)
        
        # 損失
        ax2.plot(train_losses, label='Training Loss')
        ax2.plot(val_losses, label='Validation Loss')
        ax2.set_title('Model Loss (Augmented LSTM)')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Loss')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.savefig('training_history_augmented.png')
        plt.show()
    
    def predict_player(self, sequence):
        """新しいシーケンスから選手を予測"""
        if not hasattr(self, 'model'):
            print("モデルが訓練されていません。")
            return None
        
        self.model.eval()
        
        # 学習時と同じ前処理（クリップ内で完結: 重心平行移動＋スケール正規化）
        seq_norm = DataAugmentation.normalize_sequence_center_scale(sequence)
        sequence_tensor = torch.FloatTensor(seq_norm).reshape(1, self.sequence_length, self.n_features).to(self.device)
        
        # 予測
        with torch.no_grad():
            prediction = self.model(sequence_tensor)
            probabilities = torch.softmax(prediction, dim=1)
            player_idx = torch.argmax(probabilities, dim=1).item()
            confidence = probabilities[0][player_idx].item()
        
        return self.players[player_idx], confidence

def main():
    # データパス（pose_tracks/Cleaned_Data/players/** を直接参照）
    data_path = '../pose_tracks/Cleaned_Data/players'
    
    # トレーナーを作成（各選手18サンプルに統一）
    trainer = AugmentedTennisPoseTrainer(data_path, target_samples_per_player=18)
    
    print("=== データ拡張対応テニス選手ポーズLSTMモデル ===")
    
    # データを読み込んで拡張
    X, y, player_stats, meta = trainer.load_and_augment_data()
    
    # モデルを訓練
    model = trainer.train_model(X, y, meta=meta)
    trainer.model = model
    
    print("\n=== 訓練完了 ===")
    print("保存されたファイル:")
    print("- confusion_matrix_augmented.png: 混同行列")
    print("- training_history_augmented.png: 訓練履歴")
    print("- best_augmented_model.pth: 訓練済みモデル")
    
    # 予測例
    print("\n=== 予測例 ===")
    if len(X) > 0:
        sample_sequence = X[0]
        player, confidence = trainer.predict_player(sample_sequence)
        print(f"サンプルシーケンスの予測: {player} (信頼度: {confidence:.3f})")
    
    return trainer

if __name__ == "__main__":
    trainer = main()
