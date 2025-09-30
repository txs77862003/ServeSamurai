import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

export async function POST(request: NextRequest) {
  try {
    const { userCsv, playerName } = await request.json();

    if (!userCsv || !playerName) {
      return NextResponse.json(
        { success: false, error: 'userCsv and playerName are required' },
        { status: 400 }
      );
    }

    // Pythonスクリプトのパス
    const scriptPath = path.join(process.cwd(), 'src', 'pages', 'csv_similarity_calculator.py');
    
    return new Promise((resolve) => {
      const python = spawn('python3', [scriptPath], {
        cwd: process.cwd(),
        stdio: ['pipe', 'pipe', 'pipe']
      });

      let stdout = '';
      let stderr = '';

      python.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      python.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      python.on('close', (code) => {
        if (code !== 0) {
          console.error('Python script error:', stderr);
          resolve(NextResponse.json(
            { success: false, error: `Python script failed: ${stderr}` },
            { status: 500 }
          ));
          return;
        }

        try {
          const result = JSON.parse(stdout);
          resolve(NextResponse.json(result));
        } catch (parseError) {
          console.error('JSON parse error:', parseError);
          resolve(NextResponse.json(
            { success: false, error: 'Failed to parse Python script output' },
            { status: 500 }
          ));
        }
      });

      // 入力データを送信
      python.stdin.write(JSON.stringify({ userCsv, playerName }));
      python.stdin.end();
    });

  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}