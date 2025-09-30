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

class SimpleLSTM(nn.Module):
    """シンプルなLSTMモデル"""
    def __init__(self, input_size, hidden_size=64, num_layers=2, num_classes=3, dropout=0.3):
        super(SimpleLSTM, self).__init__()
        
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

class TennisPoseLSTMTrainer:
    """テニスポーズLSTMモデルの訓練クラス"""
    def __init__(self, data_path, device=None):
        self.data_path = data_path
        self.device = device if device else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.scaler = StandardScaler()
        self.players = ['Djo', 'Fed', 'Kei']
        self.sequence_length = 48
        self.n_features = 24
        
        print(f"使用デバイス: {self.device}")
        
    def load_data(self):
        """データを読み込む"""
        print("=== データ読み込み ===")
        
        all_data = []
        all_labels = []
        
        for i, player in enumerate(self.players):
            print(f"選手 {player} のデータを読み込み中...")
            player_path = os.path.join(self.data_path, player)
            sequences = []
            
            for seq_dir in os.listdir(player_path):
                seq_path = os.path.join(player_path, seq_dir)
                if os.path.isdir(seq_path):
                    csv_file = os.path.join(seq_path, 'keypoints_with_tracks.csv')
                    if os.path.exists(csv_file):
                        df = pd.read_csv(csv_file)
                        
                        # (1)を含むフレームを除外
                        df_clean = df[~df["frame_name"].str.contains(r"\(1\)", na=False)]
                        keypoint_cols = [col for col in df_clean.columns if col.startswith('kpt_')]
                        sequence = df_clean[keypoint_cols].values
                        
                        # 48フレームのシーケンスのみを使用
                        if len(sequence) == self.sequence_length:
                            sequences.append(sequence)
            
            print(f"  - {len(sequences)} シーケンスを読み込み")
            
            # ラベルを作成
            labels = np.full(len(sequences), i)
            all_data.extend(sequences)
            all_labels.extend(labels)
        
        # データを正規化
        X = np.array(all_data)
        y = np.array(all_labels)
        
        # 正規化
        n_sequences, n_frames, n_features = X.shape
        X_flat = X.reshape(-1, n_features)
        X_normalized = self.scaler.fit_transform(X_flat)
        X_normalized = X_normalized.reshape(n_sequences, n_frames, n_features)
        
        print(f"全データ: {X_normalized.shape}")
        return X_normalized, y
    
    def train_model(self, X, y):
        """LSTMモデルを訓練"""
        print("\n=== LSTMモデル訓練 ===")
        
        # 訓練・テスト分割
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=y
        )
        
        print(f"訓練データ: {X_train.shape}, テストデータ: {X_test.shape}")
        
        # データローダーを作成
        train_dataset = TennisPoseDataset(X_train, y_train)
        test_dataset = TennisPoseDataset(X_test, y_test)
        
        train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=8, shuffle=False)
        
        # モデルを作成
        model = SimpleLSTM(
            input_size=self.n_features,
            hidden_size=64,
            num_layers=2,
            num_classes=len(self.players),
            dropout=0.3
        ).to(self.device)
        
        print(f"モデルパラメータ数: {sum(p.numel() for p in model.parameters())}")
        
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
                torch.save(model.state_dict(), 'best_lstm_model.pth')
            else:
                patience_counter += 1
            
            if epoch % 10 == 0:
                print(f'Epoch [{epoch+1}/100], Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%, Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%')
            
            if patience_counter >= patience:
                print(f'Early stopping at epoch {epoch+1}')
                break
        
        # ベストモデルを読み込み
        model.load_state_dict(torch.load('best_lstm_model.pth'))
        
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
        plt.title('Confusion Matrix (LSTM)')
        plt.ylabel('True Player')
        plt.xlabel('Predicted Player')
        plt.tight_layout()
        plt.savefig('confusion_matrix_lstm.png')
        plt.show()
        
        # 訓練履歴の可視化
        self.plot_training_history(train_losses, train_accuracies, val_losses, val_accuracies)
        
        return model
    
    def plot_training_history(self, train_losses, train_accs, val_losses, val_accs):
        """訓練履歴を可視化"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
        
        # 精度
        ax1.plot(train_accs, label='Training Accuracy')
        ax1.plot(val_accs, label='Validation Accuracy')
        ax1.set_title('Model Accuracy (LSTM)')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Accuracy (%)')
        ax1.legend()
        ax1.grid(True)
        
        # 損失
        ax2.plot(train_losses, label='Training Loss')
        ax2.plot(val_losses, label='Validation Loss')
        ax2.set_title('Model Loss (LSTM)')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Loss')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.savefig('training_history_lstm.png')
        plt.show()
    
    def predict_player(self, sequence):
        """新しいシーケンスから選手を予測"""
        if not hasattr(self, 'model'):
            print("モデルが訓練されていません。")
            return None
        
        self.model.eval()
        
        # 正規化（シーケンス全体を一度に正規化）
        sequence_normalized = self.scaler.transform(sequence.reshape(-1, self.n_features))
        sequence_tensor = torch.FloatTensor(sequence_normalized).reshape(1, self.sequence_length, self.n_features).to(self.device)
        
        # 予測
        with torch.no_grad():
            prediction = self.model(sequence_tensor)
            probabilities = torch.softmax(prediction, dim=1)
            player_idx = torch.argmax(probabilities, dim=1).item()
            confidence = probabilities[0][player_idx].item()
        
        return self.players[player_idx], confidence

def main():
    # データパス
    data_path = '../pose_tracks'
    
    # トレーナーを作成
    trainer = TennisPoseLSTMTrainer(data_path)
    
    print("=== テニス選手ポーズLSTMモデル ===")
    
    # データを読み込み
    X, y = trainer.load_data()
    
    # モデルを訓練
    model = trainer.train_model(X, y)
    trainer.model = model
    
    print("\n=== 訓練完了 ===")
    print("保存されたファイル:")
    print("- confusion_matrix_lstm.png: 混同行列")
    print("- training_history_lstm.png: 訓練履歴")
    print("- best_lstm_model.pth: 訓練済みモデル")
    
    # 予測例
    print("\n=== 予測例 ===")
    if len(X) > 0:
        sample_sequence = X[0]
        player, confidence = trainer.predict_player(sample_sequence)
        print(f"サンプルシーケンスの予測: {player} (信頼度: {confidence:.3f})")
    
    return trainer

if __name__ == "__main__":
    trainer = main()
