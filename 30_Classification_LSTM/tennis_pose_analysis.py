import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
plt.rcParams['font.family'] = 'DejaVu Sans'

class TennisPoseAnalyzer:
    def __init__(self, data_path):
        self.data_path = data_path
        # Cleaned_data/players 配下の構成に合わせてプレイヤーを拡張
        self.players = ['Djo', 'Fed', 'Kei', 'Alc']
        self.sequence_length = 48
        self.n_features = 24
        
    def load_and_analyze_data(self):
        """データを読み込んで分析"""
        print("=== データ分析開始 ===")
        
        all_data = []
        all_labels = []
        player_stats = {}
        
        for i, player in enumerate(self.players):
            print(f"\n選手 {player} のデータを分析中...")
            player_path = os.path.join(self.data_path, player)
            sequences = []
            sequence_lengths = []
            
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
                        
                        sequence_lengths.append(len(sequence))
                        
                        # 48フレームのシーケンスのみを使用
                        if len(sequence) == self.sequence_length:
                            sequences.append(sequence)
                            all_data.append(sequence)
                            all_labels.append(i)
            
            player_stats[player] = {
                'total_sequences': len(sequences),
                'sequence_lengths': sequence_lengths,
                'valid_sequences': len([s for s in sequence_lengths if s == self.sequence_length])
            }
            
            print(f"  - 総シーケンス数: {len(sequence_lengths)}")
            print(f"  - 有効シーケンス数: {player_stats[player]['valid_sequences']}")
            print(f"  - シーケンス長分布: {set(sequence_lengths)}")
        
        print(f"\n全選手の有効データ: {len(all_data)} シーケンス")
        
        if len(all_data) == 0:
            print("有効なデータがありません。")
            return None, None, None
        
        # データを正規化
        X = np.array(all_data)
        y = np.array(all_labels)
        
        # 統計的特徴を抽出
        X_features = self.extract_statistical_features(X)
        
        return X, y, X_features, player_stats
    
    def extract_statistical_features(self, sequences):
        """統計的特徴を抽出"""
        features = []
        
        for seq in sequences:
            # 各関節の統計的特徴を計算
            joint_features = []
            
            for i in range(0, self.n_features, 2):  # x, y座標ペア
                x_coords = seq[:, i]
                y_coords = seq[:, i+1]
                
                # 基本統計量
                joint_features.extend([
                    np.mean(x_coords), np.std(x_coords),
                    np.mean(y_coords), np.std(y_coords),
                    np.max(x_coords) - np.min(x_coords),  # x範囲
                    np.max(y_coords) - np.min(y_coords),  # y範囲
                ])
            
            # 全体の動きの特徴
            total_movement = np.sum(np.sqrt(np.diff(seq, axis=0)**2))
            joint_features.append(total_movement)
            
            features.append(joint_features)
        
        return np.array(features)
    
    def train_simple_classifier(self, X_features, y):
        """シンプルな分類器を訓練"""
        print("\n=== シンプル分類器の訓練 ===")
        
        # 訓練・テスト分割
        X_train, X_test, y_train, y_test = train_test_split(
            X_features, y, test_size=0.3, random_state=42, stratify=y
        )
        
        # ランダムフォレスト分類器
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        clf.fit(X_train, y_train)
        
        # 予測
        y_pred = clf.predict(X_test)
        
        # 評価
        accuracy = clf.score(X_test, y_test)
        print(f"分類精度: {accuracy:.4f}")
        
        # 分類レポート
        print("\n分類レポート:")
        print(classification_report(y_test, y_pred, target_names=self.players))
        
        # 混同行列
        cm = confusion_matrix(y_test, y_pred)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                   xticklabels=self.players, yticklabels=self.players)
        plt.title('Confusion Matrix (Random Forest)')
        plt.ylabel('True Player')
        plt.xlabel('Predicted Player')
        plt.tight_layout()
        plt.savefig('confusion_matrix_simple.png')
        plt.show()
        
        return clf
    
    def visualize_pose_data(self, X, y):
        """ポーズデータを可視化"""
        print("\n=== データ可視化 ===")
        
        # 各選手の代表的なシーケンスを選択
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()
        
        for i, player in enumerate(self.players):
            player_indices = np.where(y == i)[0]
            if len(player_indices) > 0:
                # 最初のシーケンスを使用
                seq = X[player_indices[0]]
                
                # 関節の軌跡をプロット
                ax = axes[i]
                for j in range(0, self.n_features, 2):
                    x_coords = seq[:, j]
                    y_coords = seq[:, j+1]
                    ax.plot(x_coords, y_coords, alpha=0.7, linewidth=1)
                
                ax.set_title(f'Pose Trajectory - Player {player}')
                ax.set_xlabel('X Coordinate')
                ax.set_ylabel('Y Coordinate')
                ax.invert_yaxis()  # 画像座標系に合わせる
                ax.grid(True, alpha=0.3)
        
        # 統計的特徴の分布
        ax = axes[3]
        X_features = self.extract_statistical_features(X)
        for i, player in enumerate(self.players):
            player_indices = np.where(y == i)[0]
            if len(player_indices) > 0:
                player_features = X_features[player_indices]
                # 最初の特徴（平均x座標）の分布
                ax.hist(player_features[:, 0], alpha=0.7, label=player, bins=10)
        ax.set_title('Distribution of Mean X Coordinate')
        ax.set_xlabel('Mean X Coordinate')
        ax.set_ylabel('Frequency')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 動きの量の分布
        ax = axes[4]
        for i, player in enumerate(self.players):
            player_indices = np.where(y == i)[0]
            if len(player_indices) > 0:
                player_features = X_features[player_indices]
                # 総動き量（最後の特徴）
                ax.hist(player_features[:, -1], alpha=0.7, label=player, bins=10)
        ax.set_title('Distribution of Total Movement')
        ax.set_xlabel('Total Movement')
        ax.set_ylabel('Frequency')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # シーケンス長の分布
        ax = axes[5]
        sequence_lengths = [len(seq) for seq in X]
        ax.hist(sequence_lengths, bins=20, alpha=0.7)
        ax.set_title('Distribution of Sequence Length')
        ax.set_xlabel('Number of Frames')
        ax.set_ylabel('Frequency')
        ax.axvline(self.sequence_length, color='red', linestyle='--', label=f'Target Length: {self.sequence_length}')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('pose_visualization.png')
        plt.show()
    
    def generate_report(self, player_stats, clf=None):
        """分析レポートを生成"""
        print("\n=== 分析レポート ===")
        
        print("\n1. データ概要:")
        total_sequences = sum(stats['total_sequences'] for stats in player_stats.values())
        valid_sequences = sum(stats['valid_sequences'] for stats in player_stats.values())
        
        print(f"   - 総シーケンス数: {total_sequences}")
        print(f"   - 有効シーケンス数: {valid_sequences}")
        print(f"   - 有効率: {valid_sequences/total_sequences*100:.1f}%")
        
        print("\n2. 選手別統計:")
        for player, stats in player_stats.items():
            print(f"   - {player}: {stats['valid_sequences']}/{stats['total_sequences']} シーケンス")
            print(f"     シーケンス長: {set(stats['sequence_lengths'])}")
        
        if clf is not None:
            print("\n3. 特徴重要度 (上位10個):")
            feature_importance = clf.feature_importances_
            top_features = np.argsort(feature_importance)[-10:][::-1]
            for i, feat_idx in enumerate(top_features):
                print(f"   {i+1}. 特徴 {feat_idx}: {feature_importance[feat_idx]:.4f}")
        
        print("\n4. 今後の展開提案:")
        print("   - LSTMモデルの実装（時系列データの活用）")
        print("   - より多くの特徴量の抽出（速度、加速度など）")
        print("   - データ拡張技術の適用")
        print("   - 深層学習モデルの実装")
        print("   - リアルタイム予測システムの構築")

def main():
    # pose_tracks/Cleaned_Data/players/<Player>/<Clip>/keypoints_with_tracks.csv に対応
    data_path = '../pose_tracks/Cleaned_Data/players'
    analyzer = TennisPoseAnalyzer(data_path)
    
    # データを読み込んで分析
    X, y, X_features, player_stats = analyzer.load_and_analyze_data()
    
    if X is not None:
        # データを可視化
        analyzer.visualize_pose_data(X, y)
        
        # シンプルな分類器を訓練
        clf = analyzer.train_simple_classifier(X_features, y)
        
        # レポートを生成
        analyzer.generate_report(player_stats, clf)
        
        print("\n=== 分析完了 ===")
        print("保存されたファイル:")
        print("- confusion_matrix_simple.png: 混同行列")
        print("- pose_visualization.png: データ可視化")
    else:
        print("有効なデータが見つかりませんでした。")

if __name__ == "__main__":
    main()
