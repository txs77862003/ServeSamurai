import pandas as pd
import numpy as np
import os
import glob
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')


class TennisPoseDataset(Dataset):
    """テニスポーズデータセット用のPyTorch Dataset"""
    def __init__(self, sequences, labels=None, is_regression=False):
        self.sequences = torch.FloatTensor(sequences)
        if labels is not None:
            if is_regression:
                self.labels = torch.FloatTensor(labels)
            else:
                self.labels = torch.LongTensor(labels)
        else:
            self.labels = None
        
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        if self.labels is not None:
            return self.sequences[idx], self.labels[idx]
        return self.sequences[idx]

class TennisPoseLSTM(nn.Module):
    """テニスポーズ用LSTMモデル"""
    def __init__(self, input_size, hidden_size=128, num_layers=3, num_classes=3, dropout=0.3):
        super(TennisPoseLSTM, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM層
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, 
                           batch_first=True, dropout=dropout if num_layers > 1 else 0)
        
        # バッチ正規化
        self.batch_norm = nn.BatchNorm1d(hidden_size)
        
        # 全結合層
        self.fc_layers = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(dropout/2),
            nn.Linear(32, num_classes)
        )
        
    def forward(self, x):
        # LSTMの出力
        lstm_out, (hidden, cell) = self.lstm(x)
        
        # 最後のタイムステップの出力を使用
        last_output = lstm_out[:, -1, :]
        
        # バッチ正規化
        normalized = self.batch_norm(last_output)
        
        # 全結合層
        output = self.fc_layers(normalized)
        
        return output

class TennisPoseRegressor(nn.Module):
    """次のフレーム予測用の回帰モデル"""
    def __init__(self, input_size, hidden_size=64, num_layers=2, output_size=24, dropout=0.2):
        super(TennisPoseRegressor, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM層
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, 
                           batch_first=True, dropout=dropout if num_layers > 1 else 0)
        
        # 全結合層
        self.fc_layers = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, output_size)
        )
        
    def forward(self, x):
        # LSTMの出力
        lstm_out, (hidden, cell) = self.lstm(x)
        
        # 最後のタイムステップの出力を使用
        if len(lstm_out.shape) == 3:
            last_output = lstm_out[:, -1, :]
        else:
            last_output = lstm_out
        
        # 全結合層
        output = self.fc_layers(last_output)
        
        return output

class TennisPoseTrainer:
    """テニスポーズLSTMモデルの訓練クラス"""
    def __init__(self, data_path, device=None):
        self.data_path = data_path
        self.device = device if device else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.scaler = StandardScaler()
        self.models = {}
        self.players = ['Djo', 'Fed', 'Kei']
        self.sequence_length = 48
        self.n_features = 24
        
        print(f"使用デバイス: {self.device}")
        
    def load_player_data(self, player):
        """指定された選手のデータを読み込む"""
        player_path = os.path.join(self.data_path, player)
        sequences = []
        
        for seq_dir in os.listdir(player_path):
            seq_path = os.path.join(player_path, seq_dir)
            if os.path.isdir(seq_path):
                csv_file = os.path.join(seq_path, 'keypoints_with_tracks.csv')
                if os.path.exists(csv_file):
                    df = pd.read_csv(csv_file)
                    df = df[~df["frame_name"].str.contains(r"\(1\)", na=False)]
                    keypoint_cols = [col for col in df.columns if col.startswith('kpt_')]
                    sequence = df[keypoint_cols].values
                    
                    # シーケンスの長さを統一（48フレームに調整）
                    if len(sequence) > self.sequence_length:
                        # 長すぎる場合は中央部分を切り出し
                        print(f"選手 {player} のデータが長すぎます。スキップします。")
                        continue
                    elif len(sequence) < self.sequence_length:
                        # 短すぎる場合は最後のフレームを繰り返し
                        print(f"選手 {player} のデータが不足しています。スキップします。")
                        continue
                    
                    sequences.append(sequence)
        
        return np.array(sequences)
    
    def preprocess_data(self, sequences):
        """データの前処理と正規化"""
        n_sequences, n_frames, n_features = sequences.shape
        sequences_flat = sequences.reshape(-1, n_features)
        
        # 正規化
        sequences_normalized = self.scaler.fit_transform(sequences_flat)
        
        # 元の形状に戻す
        sequences_normalized = sequences_normalized.reshape(n_sequences, n_frames, n_features)
        
        return sequences_normalized
    
    def train_classification_model(self):
        """選手分類モデルを訓練"""
        print("=== 選手分類モデルの訓練 ===")
        
        # 全選手のデータを収集
        all_data = []
        all_labels = []
        
        for i, player in enumerate(self.players):
            print(f"選手 {player} のデータを読み込み中...")
            sequences = self.load_player_data(player)
            print(f"  - {len(sequences)} シーケンスを読み込み")
            
            sequences_normalized = self.preprocess_data(sequences)
            all_data.append(sequences_normalized)
            
            labels = np.full(len(sequences), i)
            all_labels.append(labels)
        
        # データを結合
        X = np.vstack(all_data)
        y = np.hstack(all_labels)
        
        # 訓練・テスト分割
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"訓練データ: {X_train.shape}, テストデータ: {X_test.shape}")
        
        # データローダーを作成
        train_dataset = TennisPoseDataset(X_train, y_train)
        test_dataset = TennisPoseDataset(X_test, y_test)
        
        train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)
        
        # モデルを作成
        model = TennisPoseLSTM(
            input_size=self.n_features,
            hidden_size=128,
            num_layers=3,
            num_classes=len(self.players),
            dropout=0.3
        ).to(self.device)
        
        # 損失関数とオプティマイザー
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=0.5)
        
        # 訓練
        train_losses = []
        train_accuracies = []
        val_losses = []
        val_accuracies = []
        
        best_val_acc = 0
        patience = 20
        patience_counter = 0
        
        print("訓練開始...")
        for epoch in range(100):
            # 訓練フェーズ
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
            
            # 検証フェーズ
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
            
            # メトリクス計算
            train_loss /= len(train_loader)
            train_acc = 100 * train_correct / train_total
            val_loss /= len(test_loader)
            val_acc = 100 * val_correct / val_total
            
            train_losses.append(train_loss)
            train_accuracies.append(train_acc)
            val_losses.append(val_loss)
            val_accuracies.append(val_acc)
            
            # 学習率スケジューラー
            scheduler.step(val_loss)
            
            # 早期停止チェック
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                patience_counter = 0
                # ベストモデルを保存
                torch.save(model.state_dict(), 'best_classification_model.pth')
            else:
                patience_counter += 1
            
            if epoch % 10 == 0:
                print(f'Epoch [{epoch+1}/100], Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%, Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%')
            
            if patience_counter >= patience:
                print(f'Early stopping at epoch {epoch+1}')
                break
        
        # ベストモデルを読み込み
        model.load_state_dict(torch.load('best_classification_model.pth'))
        
        # 最終評価
        model.eval()
        all_predictions = []
        all_targets = []
        
        with torch.no_grad():
            for batch_x, batch_y in test_loader:
                batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                outputs = model(batch_x)
                _, predicted = torch.max(outputs.data, 1)
                all_predictions.extend(predicted.cpu().numpy())
                all_targets.extend(batch_y.cpu().numpy())
        
        # 分類レポート
        print(f"\n最終テスト精度: {best_val_acc:.2f}%")
        print("\n分類レポート:")
        print(classification_report(all_targets, all_predictions, target_names=self.players))
        
        # 混同行列
        cm = confusion_matrix(all_targets, all_predictions)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                   xticklabels=self.players, yticklabels=self.players)
        plt.title('Confusion Matrix (PyTorch)')
        plt.ylabel('True Player')
        plt.xlabel('Predicted Player')
        plt.tight_layout()
        plt.savefig('confusion_matrix_pytorch.png')
        plt.show()
        
        # 訓練履歴の可視化
        self.plot_training_history(train_losses, train_accuracies, val_losses, val_accuracies)
        
        self.models['classification'] = model
        self.scaler_classification = self.scaler
        
        return model
    
    def train_regression_models(self):
        """各選手の回帰モデルを訓練"""
        print("\n=== 各選手の回帰モデル訓練 ===")
        
        for player in self.players:
            print(f"\n選手 {player} の回帰モデルを訓練中...")
            
            # 選手のデータを読み込み
            sequences = self.load_player_data(player)
            sequences_normalized = self.preprocess_data(sequences)
            
            # 次のフレーム予測用のデータを準備
            X, y = self.prepare_prediction_data(sequences_normalized)
            
            if len(X) < 2:
                print(f"選手 {player} のデータが不足しています。スキップします。")
                continue
            
            # 訓練・テスト分割
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # データローダー
            train_dataset = TennisPoseDataset(X_train, y_train, is_regression=True)
            test_dataset = TennisPoseDataset(X_test, y_test, is_regression=True)
            
            train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True)
            test_loader = DataLoader(test_dataset, batch_size=8, shuffle=False)
            
            # モデルを作成
            model = TennisPoseRegressor(
                input_size=self.n_features,
                hidden_size=64,
                num_layers=2,
                output_size=self.n_features,
                dropout=0.2
            ).to(self.device)
            
            # 損失関数とオプティマイザー
            criterion = nn.MSELoss()
            optimizer = optim.Adam(model.parameters(), lr=0.001)
            scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=8, factor=0.5)
            
            # 訓練
            best_val_loss = float('inf')
            patience = 15
            patience_counter = 0
            
            for epoch in range(50):
                # 訓練フェーズ
                model.train()
                train_loss = 0
                
                for batch_x, batch_y in train_loader:
                    batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                    
                    optimizer.zero_grad()
                    outputs = model(batch_x)
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    optimizer.step()
                    
                    train_loss += loss.item()
                
                # 検証フェーズ
                model.eval()
                val_loss = 0
                
                with torch.no_grad():
                    for batch_x, batch_y in test_loader:
                        batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                        outputs = model(batch_x)
                        loss = criterion(outputs, batch_y)
                        val_loss += loss.item()
                
                train_loss /= len(train_loader)
                val_loss /= len(test_loader)
                
                scheduler.step(val_loss)
                
                # 早期停止チェック
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    torch.save(model.state_dict(), f'best_regression_model_{player}.pth')
                else:
                    patience_counter += 1
                
                if epoch % 10 == 0:
                    print(f'  Epoch [{epoch+1}/50], Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}')
                
                if patience_counter >= patience:
                    print(f'  Early stopping at epoch {epoch+1}')
                    break
            
            # ベストモデルを読み込み
            model.load_state_dict(torch.load(f'best_regression_model_{player}.pth'))
            self.models[f'regression_{player}'] = model
            
            print(f"選手 {player} の回帰モデル訓練完了")
    
    def prepare_prediction_data(self, sequences):
        """次のフレーム予測用のデータを準備"""
        X, y = [], []
        for seq in sequences:
            for i in range(len(seq) - 1):
                X.append(seq[i:i+1])  # シーケンス形状を保持
                y.append(seq[i + 1])
        return np.array(X), np.array(y)
    
    def plot_training_history(self, train_losses, train_accs, val_losses, val_accs):
        """訓練履歴を可視化"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
        
        # 精度
        ax1.plot(train_accs, label='Training Accuracy')
        ax1.plot(val_accs, label='Validation Accuracy')
        ax1.set_title('Model Accuracy (PyTorch)')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Accuracy (%)')
        ax1.legend()
        ax1.grid(True)
        
        # 損失
        ax2.plot(train_losses, label='Training Loss')
        ax2.plot(val_losses, label='Validation Loss')
        ax2.set_title('Model Loss (PyTorch)')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Loss')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.savefig('training_history_pytorch.png')
        plt.show()
    
    def predict_player(self, sequence):
        """新しいシーケンスから選手を予測"""
        if 'classification' not in self.models:
            print("分類モデルが訓練されていません。")
            return None
        
        model = self.models['classification']
        model.eval()
        
        # 正規化
        sequence_normalized = self.scaler_classification.transform(sequence.reshape(1, -1))
        sequence_tensor = torch.FloatTensor(sequence_normalized).reshape(1, self.sequence_length, self.n_features).to(self.device)
        
        # 予測
        with torch.no_grad():
            prediction = model(sequence_tensor)
            probabilities = torch.softmax(prediction, dim=1)
            player_idx = torch.argmax(probabilities, dim=1).item()
            confidence = probabilities[0][player_idx].item()
        
        return self.players[player_idx], confidence
    
    def predict_next_frame(self, player, sequence):
        """指定された選手の次のフレームを予測"""
        model_key = f'regression_{player}'
        if model_key not in self.models:
            print(f"選手 {player} の回帰モデルがありません。")
            return None
        
        model = self.models[model_key]
        model.eval()
        
        # 正規化（選手固有のスケーラーが必要）
        sequence_tensor = torch.FloatTensor(sequence).reshape(1, -1, self.n_features).to(self.device)
        
        # 予測
        with torch.no_grad():
            next_frame = model(sequence_tensor)
        
        return next_frame[0].cpu().numpy()

def main():
    # データパス
    data_path = '../pose_tracks'
    
    # トレーナーを作成
    trainer = TennisPoseTrainer(data_path)
    
    print("=== テニス選手ポーズLSTMモデル (PyTorch) ===")
    
    # 分類モデルを訓練
    classification_model = trainer.train_classification_model()
    
    # 回帰モデルを訓練
    trainer.train_regression_models()
    
    print("\n=== 訓練完了 ===")
    print("保存されたファイル:")
    print("- confusion_matrix_pytorch.png: 混同行列")
    print("- training_history_pytorch.png: 訓練履歴")
    print("- best_classification_model.pth: 分類モデル")
    print("- best_regression_model_[player].pth: 各選手の回帰モデル")
    
    return trainer

if __name__ == "__main__":
    trainer = main()
